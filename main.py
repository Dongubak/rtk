import socket
import base64
import serial
import time
import threading

# ── 설정 ──────────────────────────────────────────
# COM       = '/dev/tty.usbserial-1440'        # Linux: /dev/ttyUSB0, Windows: COM15
# COM = '/dev/tty.usbserial-130'
# COM = '/dev/tty.usbserial-2130'
# COM = '/dev/tty.usbserial-21420'
COM = '/dev/tty.usbserial-21430'
BPS       = 460800          # set_baud.py 로 수신기 속도 변경 후 사용 (115200 은 보정량 초과로 RTK 불가)
NtripIP    = 'RTS1.ngii.go.kr'
NtripPort  = 2101
NtripUser  = 'hyuk6578'
NtripPwd   = 'ngii'
NtripPoint = 'VRS-RTCM34'    # GPS+GLO+GAL+BDS+QZS (5종 위성)
# ──────────────────────────────────────────────────

RTK = serial.Serial(COM, BPS, timeout=1)
print("RTK 모듈 연결됨. GGA 대기 중...")

# 1. 초기 GGA 수신
strGNGGA = None
while strGNGGA is None:
    data = RTK.readline()
    if not data:
        continue
    try:
        line = data.decode("ascii", errors="ignore").strip()
    except:
        continue
    seg = line.split(',')
    if seg[0] in ("$GNGGA", "$GPGGA") and len(seg) > 6 and seg[6] not in ('', '0'):
        strGNGGA = line + "\r\n"
        print(f"GGA 수신: {strGNGGA.strip()}")

# 2. NTRIP 접속 (함수화 — 끊기면 재접속에 재사용)
user_pwd = base64.b64encode(f"{NtripUser}:{NtripPwd}".encode()).decode()
httpHead = (
    f"GET /{NtripPoint} HTTP/1.0\r\n"
    f"User-Agent: NTRIP PythonClient/1.0\r\n"
    f"Accept: */*\r\n"
    f"Connection: close\r\n"
    f"Authorization: Basic {user_pwd}\r\n\r\n"
)

latest_gga = strGNGGA      # 메인 루프가 최신 GGA로 갱신 → 재접속 시 사용

def connect_ntrip():
    """NTRIP 서버에 접속해 핸드셰이크 + GGA 전송. 실패 시 None."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((NtripIP, NtripPort))
        s.send(httpHead.encode())
        resp = s.recv(1024).decode("ascii", errors="ignore")
        if "200 OK" not in resp and "ICY 200 OK" not in resp:
            print(f"❌ NTRIP 응답 이상: {resp[:50]}")
            s.close()
            return None
        s.send(latest_gga.encode())
        return s
    except Exception as e:
        print(f"⚠️  NTRIP 접속 실패: {e}")
        return None

print(f"NTRIP 서버 접속 중: {NtripIP}:{NtripPort}/{NtripPoint}")
ntrip = connect_ntrip()
while ntrip is None:           # 최초 접속도 될 때까지 재시도
    time.sleep(2)
    print("…NTRIP 재시도")
    ntrip = connect_ntrip()
print("✅ NTRIP 접속 성공. RTCM 수신 시작...")

# 3. RTCM 보정 전달 스레드 (끊기면 자동 재접속)
def rtcm_forwarder():
    global ntrip
    while True:
        try:
            rtcm = ntrip.recv(4096)
            if rtcm:
                RTK.write(rtcm)
            else:
                raise ConnectionError("서버가 연결 종료(빈 응답)")
        except socket.timeout:
            continue
        except Exception as e:
            print(f"⚠️  RTCM 끊김({e}) → 재접속 시도")
            try:
                ntrip.close()
            except Exception:
                pass
            time.sleep(2)
            new = connect_ntrip()
            if new is not None:
                ntrip = new
                print("🔄 NTRIP 재접속 성공")

threading.Thread(target=rtcm_forwarder, daemon=True).start()

# 4. 메인 루프 — NMEA 읽기(Fixed 상태 모니터링)만 담당
gga_timer = time.time()

while True:
    nmea = RTK.readline()
    if not nmea:
        continue
    try:
        line = nmea.decode("ascii", errors="ignore").strip()
        if "$GNGGA" in line or "$GPGGA" in line:
            seg = line.split(',')
            fix_type = seg[6] if len(seg) > 6 else '?'
            num_sat = seg[7] if len(seg) > 7 else '?'
            hdop    = seg[8] if len(seg) > 8 else '?'
            # fix_type: 0=없음, 1=GPS, 2=DGPS, 4=RTK Fixed, 5=RTK Float
            status = {
                '0': '❌ No Fix',
                '1': '🟡 GPS only',
                '2': '🔵 DGPS (보정 적용중)',
                '4': '✅ RTK Fixed',
                '5': '🟠 RTK Float'
            }.get(fix_type, f'? ({fix_type})')
            print(f"상태: {status} | 위성 {num_sat}개 | HDOP {hdop}")

            # 재접속 시 사용할 최신 GGA 갱신
            if fix_type not in ('', '0'):
                latest_gga = line + "\r\n"

            # 10초마다 GGA 재전송 (VRS가 가상기준국을 최신 위치로 유지)
            if time.time() - gga_timer > 10:
                try:
                    ntrip.send((line + "\r\n").encode())
                except Exception:
                    pass            # 끊김은 forwarder 스레드가 재접속 처리
                gga_timer = time.time()
    except Exception:
        pass