import socket
import base64
import serial
import time
from collections import Counter

# ── 설정 ──────────────────────────────────────────
# COM        = '/dev/tty.usbserial-1440'
# COM = '/dev/tty.usbserial-130'
# COM = '/dev/tty.usbserial-2130'
# COM = '/dev/tty.usbserial-21420'
COM = '/dev/tty.usbserial-21430'
BPS        = 460800          # set_baud.py 실행 후 (이전: 115200)
NtripIP    = 'RTS1.ngii.go.kr'
NtripPort  = 2101
NtripUser  = 'hyuk6578'
NtripPwd   = 'ngii'
NtripPoint = 'VRS-RTCM34'    # GPS+GLO+GAL+BDS+QZS (5종 위성)
# ──────────────────────────────────────────────────

# RTCM 3.x 메시지 타입 설명 (대표적인 것들)
RTCM_DESC = {
    1004: "GPS L1/L2 관측 (legacy)",
    1005: "Station coord ARP",
    1006: "Station coord ARP + height",
    1007: "Antenna descriptor",
    1012: "GLONASS L1/L2 관측 (legacy)",
    1019: "GPS ephemeris",
    1020: "GLONASS ephemeris",
    1033: "Receiver/antenna descriptor",
    1042: "BeiDou ephemeris",
    1045: "Galileo F/NAV ephemeris",
    1046: "Galileo I/NAV ephemeris",
    1074: "GPS MSM4",
    1075: "GPS MSM5",
    1077: "GPS MSM7",
    1084: "GLONASS MSM4",
    1085: "GLONASS MSM5",
    1087: "GLONASS MSM7",
    1094: "Galileo MSM4",
    1095: "Galileo MSM5",
    1097: "Galileo MSM7",
    1124: "BeiDou MSM4",
    1125: "BeiDou MSM5",
    1127: "BeiDou MSM7",
    1230: "GLONASS L1/L2 code-phase biases",
}

def parse_rtcm(buf, type_counter):
    """0xD3 프리앰블 단위로 RTCM 메시지를 잘라서 타입만 추출"""
    i = 0
    types = []
    while i < len(buf) - 6:
        if buf[i] != 0xD3:
            i += 1
            continue
        length = ((buf[i+1] & 0x03) << 8) | buf[i+2]
        end = i + 3 + length + 3   # 헤더(3) + payload + CRC(3)
        if end > len(buf):
            break
        if length >= 2:
            msg_type = (buf[i+3] << 4) | (buf[i+4] >> 4)
            types.append(msg_type)
            type_counter[msg_type] += 1
        i = end
    return types, buf[i:]   # 남은 미완성 바이트는 다음 회차에 처리


# ── 시작 ──────────────────────────────────────────
RTK = serial.Serial(COM, BPS, timeout=0.2)
print("RTK 모듈 연결됨. GGA 대기 중...\n")

strGNGGA = None
while strGNGGA is None:
    data = RTK.readline()
    if not data:
        continue
    line = data.decode("ascii", errors="ignore").strip()
    print(f"[NMEA] {line}")
    seg = line.split(',')
    if seg[0] in ("$GNGGA", "$GPGGA") and len(seg) > 6 and seg[6] not in ('', '0'):
        strGNGGA = line + "\r\n"
        print(f"\n✅ GGA 확보: {strGNGGA.strip()}\n")

# NTRIP 접속
print(f"NTRIP 접속: {NtripIP}:{NtripPort}/{NtripPoint}")
ntrip = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ntrip.connect((NtripIP, NtripPort))
ntrip.settimeout(5)

user_pwd = base64.b64encode(f"{NtripUser}:{NtripPwd}".encode()).decode()
httpHead = (
    f"GET /{NtripPoint} HTTP/1.0\r\n"
    f"User-Agent: NTRIP PythonClient/1.0\r\n"
    f"Accept: */*\r\n"
    f"Connection: close\r\n"
    f"Authorization: Basic {user_pwd}\r\n\r\n"
)
ntrip.send(httpHead.encode())
resp = ntrip.recv(1024).decode("ascii", errors="ignore")
print(f"서버 응답: {resp.strip()[:80]}")
if "200 OK" not in resp and "ICY 200 OK" not in resp:
    print("❌ NTRIP 접속 실패")
    exit()

ntrip.send(strGNGGA.encode())
print("✅ NTRIP 접속 성공. 메시지 모니터링 시작...\n")
print("=" * 60)

# ── 메인 루프 ─────────────────────────────────────
rtcm_buf = b''
type_counter = Counter()
nmea_counter = Counter()
total_rtcm_bytes = 0
gga_timer = time.time()
report_timer = time.time()
last_status = None

while True:
    # 1) NTRIP → RTCM 수신
    try:
        rtcm = ntrip.recv(4096)
        if rtcm:
            total_rtcm_bytes += len(rtcm)
            RTK.write(rtcm)
            rtcm_buf += rtcm
            types, rtcm_buf = parse_rtcm(rtcm_buf, type_counter)
            for t in types:
                desc = RTCM_DESC.get(t, "?")
                print(f"[RTCM] type {t:<5} {desc}")
    except socket.timeout:
        pass

    # 2) RTK 모듈 → NMEA 수신
    nmea = RTK.readline()
    if nmea:
        line = nmea.decode("ascii", errors="ignore").strip()
        if not line:
            continue
        seg = line.split(',')
        talker = seg[0] if seg else "?"
        nmea_counter[talker] += 1

        # GGA는 fix 상태도 같이 표시
        if talker in ("$GNGGA", "$GPGGA") and len(seg) > 6:
            fix_type = seg[6]
            sats = seg[7] if len(seg) > 7 else '?'
            hdop = seg[8] if len(seg) > 8 else '?'
            status_map = {
                '0': '❌ No Fix', '1': '🟡 GPS', '2': '🔵 DGPS',
                '4': '✅ RTK Fixed', '5': '🟠 RTK Float'
            }
            status = status_map.get(fix_type, f'? ({fix_type})')
            msg = f"[NMEA] GGA  fix={status}  sats={sats}  HDOP={hdop}"
            if status != last_status:
                print(f"\n>>> 상태 변경: {status}\n")
                last_status = status
            print(msg)
        else:
            print(f"[NMEA] {line}")

        # 30초마다 GGA 재전송
        if talker in ("$GNGGA", "$GPGGA") and time.time() - gga_timer > 30:
            ntrip.send((line + "\r\n").encode())
            gga_timer = time.time()

    # 3) 10초마다 요약 리포트
    if time.time() - report_timer > 10:
        print("\n" + "─" * 60)
        print(f"📊 10초 요약  (RTCM 누적: {total_rtcm_bytes:,} bytes)")
        print(f"   NMEA: {dict(nmea_counter)}")
        print(f"   RTCM types: {dict(type_counter)}")
        print("─" * 60 + "\n")
        report_timer = time.time()
