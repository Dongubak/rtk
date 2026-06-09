"""
RTK Fixed 정확도 테스트 (한국 좌표계 EPSG:5186, 단위 m).

정지 상태에서 RTK Fixed 위치를 모아 한국 중부원점 좌표로 변환하고,
반복정밀도(scatter)를 cm 단위로 측정한다. (Fixed=4 인 샘플만 사용)

준비:  pip install pyproj
실행:  python accuracy_test.py        (Ctrl+C 로 종료)

※ 기준점 참값(REF_LAT/REF_LON)을 알면 절대 오차도 함께 출력한다.
"""
import socket, base64, serial, time, threading, glob, math, statistics
from pyproj import Transformer

BPS  = 460800
IP, PORT = 'RTS1.ngii.go.kr', 2101
USER, PWD, MP = 'hyuk6578', 'ngii', 'VRS-RTCM34'

# (선택) 측량된 기준점 참값 — 모르면 None. 알면 절대오차 계산됨.
REF_LAT, REF_LON = None, None

# WGS84(GPS) → Korea 2000 중부원점(EPSG:5186) [126~128°E]
tf = Transformer.from_crs("EPSG:4326", "EPSG:5186", always_xy=True)


def nmea_deg(v):                 # ddmm.mmmm → 십진수 도
    d = int(v // 100)
    return d + (v - d * 100) / 60


# 포트 자동 탐지
ports = glob.glob('/dev/tty.usbserial*')
if not ports:
    raise SystemExit("❌ USB 시리얼 포트 없음 — 연결 확인")
COM = ports[0]
RTK = serial.Serial(COM, BPS, timeout=1)

# 초기 GGA 확보
gga = None
while gga is None:
    d = RTK.readline().decode("ascii", "ignore").strip()
    s = d.split(',')
    if s and s[0] in ("$GNGGA", "$GPGGA") and len(s) > 6 and s[6] not in ('', '0'):
        gga = d + "\r\n"

# NTRIP 접속 + RTCM 전달 스레드
n = socket.socket(); n.connect((IP, PORT)); n.settimeout(5)
auth = base64.b64encode(f"{USER}:{PWD}".encode()).decode()
n.send((f"GET /{MP} HTTP/1.0\r\nUser-Agent: NTRIP\r\nAccept: */*\r\n"
        f"Connection: close\r\nAuthorization: Basic {auth}\r\n\r\n").encode())
n.recv(1024); n.send(gga.encode())
print(f"포트 {COM} @ {BPS}, NTRIP 접속됨. RTK Fixed 대기 중...\n")


def fwd():
    while True:
        try:
            r = n.recv(4096)
            if r:
                RTK.write(r)
        except socket.timeout:
            pass
        except Exception:
            break


threading.Thread(target=fwd, daemon=True).start()

xs, ys, hs = [], [], []
last_gga = time.time()
try:
    while True:
        line = RTK.readline().decode("ascii", "ignore").strip()
        if line.startswith("$") and ("GNGGA" in line or "GPGGA" in line):
            seg = line.split(',')
            if len(seg) >= 10 and seg[6]:
                if seg[6] != '4':                      # Fixed(4) 만 수집
                    print(f"  대기: fix={seg[6]} (4=Fixed 아님)")
                else:
                    lat = nmea_deg(float(seg[2])); lat = -lat if seg[3] == 'S' else lat
                    lon = nmea_deg(float(seg[4])); lon = -lon if seg[5] == 'W' else lon
                    h = float(seg[9])
                    x, y = tf.transform(lon, lat)      # always_xy → (경도, 위도)
                    xs.append(x); ys.append(y); hs.append(h)
                    k = len(xs)
                    if k >= 2 and k % 5 == 0:
                        mx, my, mh = statistics.mean(xs), statistics.mean(ys), statistics.mean(hs)
                        sx, sy, sh = statistics.pstdev(xs), statistics.pstdev(ys), statistics.pstdev(hs)
                        h2d = math.hypot(sx, sy)
                        print(f"[{k:3d}샘플] 평균 X={mx:.3f} Y={my:.3f} H={mh:.3f} m | "
                              f"수평σ={h2d*100:5.1f}cm (X{sx*100:.1f}/Y{sy*100:.1f}) 수직σ={sh*100:5.1f}cm")
                        if REF_LAT is not None:
                            rx, ry = tf.transform(REF_LON, REF_LAT)
                            print(f"          └ 기준점 대비 수평오차 {math.hypot(mx-rx, my-ry)*100:.1f}cm")
            # VRS 유지용 GGA 재전송
            if time.time() - last_gga > 10:
                n.send((line + "\r\n").encode()); last_gga = time.time()
except KeyboardInterrupt:
    if xs:
        sx, sy, sh = statistics.pstdev(xs), statistics.pstdev(ys), statistics.pstdev(hs)
        print(f"\n=== 최종 ({len(xs)}샘플) 수평σ={math.hypot(sx,sy)*100:.1f}cm 수직σ={sh*100:.1f}cm ===")
    RTK.close(); n.close()
