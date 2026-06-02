import socket
import base64
import serial
import time

# ── 설정 ──────────────────────────────────────────
COM       = '/dev/tty.usbserial-1440'        # Linux: /dev/ttyUSB0, Windows: COM15
BPS       = 115200
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

# 2. NTRIP 접속
print(f"NTRIP 서버 접속 중: {NtripIP}:{NtripPort}/{NtripPoint}")
ntrip = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ntrip.connect((NtripIP, NtripPort))
ntrip.settimeout(5)                  # ← 블로킹 방지

user_pwd = base64.b64encode(
    f"{NtripUser}:{NtripPwd}".encode()
).decode()

httpHead = (
    f"GET /{NtripPoint} HTTP/1.0\r\n"
    f"User-Agent: NTRIP PythonClient/1.0\r\n"
    f"Accept: */*\r\n"
    f"Connection: close\r\n"
    f"Authorization: Basic {user_pwd}\r\n\r\n"
)
ntrip.send(httpHead.encode())

# 서버 응답 확인
resp = ntrip.recv(1024).decode("ascii", errors="ignore")
print(f"서버 응답: {resp[:50]}")
if "200 OK" not in resp and "ICY 200 OK" not in resp:
    print("❌ NTRIP 접속 실패. 계정/마운트포인트 확인 필요")
    exit()

# GGA 전송 (서버가 근처 RTCM 선택하도록)
ntrip.send(strGNGGA.encode())
print("✅ NTRIP 접속 성공. RTCM 수신 시작...")

# 3. 메인 루프
gga_timer = time.time()

while True:
    # RTCM 수신 → RTK 모듈로 전달
    try:
        rtcm = ntrip.recv(4096)
        if rtcm:
            RTK.write(rtcm)
    except socket.timeout:
        pass

    # NMEA 읽기 (Fixed 상태 모니터링)
    nmea = RTK.readline()
    if nmea:
        try:
            line = nmea.decode("ascii", errors="ignore").strip()
            if "$GNGGA" in line or "$GPGGA" in line:
                seg = line.split(',')
                fix_type = seg[6] if len(seg) > 6 else '?'
                # fix_type: 0=없음, 1=GPS, 2=DGPS, 4=RTK Fixed, 5=RTK Float
                status = {
                    '0': '❌ No Fix',
                    '1': '🟡 GPS only',
                    '2': '🔵 DGPS (보정 적용중)',
                    '4': '✅ RTK Fixed',
                    '5': '🟠 RTK Float'
                }.get(fix_type, f'? ({fix_type})')
                print(f"상태: {status}")

                # 30초마다 GGA 재전송 (서버 연결 유지)
                if time.time() - gga_timer > 30:
                    ntrip.send((line + "\r\n").encode())
                    gga_timer = time.time()
        except:
            pass