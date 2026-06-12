"""
COM1 을 9600 baud 로 설정하고 GNRMC 를 1Hz 출력하도록 구성 + 영구 저장.
명령은 USB(COM3, 460800)로 전송한다. COM1 은 TTL 로 따로 읽는다.

    python set_com1_rmc.py
"""
import serial, time, glob, sys

BPS = 460800   # USB(COM3) 접속 속도
RMC = "GNRMC"  # GPS만 원하면 "GPRMC"

ports = glob.glob('/dev/tty.usbserial*')
if not ports:
    sys.exit("❌ USB 시리얼 포트 없음 — 연결 확인")
COM = ports[0]
print(f"USB 접속: {COM} @ {BPS}\n")

ser = serial.Serial(COM, BPS, timeout=1)
time.sleep(0.4); ser.reset_input_buffer()

cmds = [
    "CONFIG COM1 9600",
    "UNLOGALL COM1",
    f"LOG COM1 {RMC} ONTIME 1",
    "SAVECONFIG",
]
for c in cmds:
    ser.reset_input_buffer()
    ser.write((c + "\r\n").encode())
    time.sleep(0.7)
    print(f">>> {c}")
    while ser.in_waiting:
        l = ser.readline().decode("ascii", "ignore").strip()
        if "response" in l or "FAIL" in l or "error" in l.lower():
            print("   ", l)

# 확인
ser.reset_input_buffer()
ser.write(b"CONFIG\r\n"); time.sleep(1.2)
print("\n=== 확인 (COM1 / LOG) ===")
while ser.in_waiting:
    l = ser.readline().decode("ascii", "ignore").strip()
    if "COM1" in l or (RMC in l):
        print("  ", l)
ser.close()
print("\n✅ 완료. COM1 TXD 를 TTL 모듈 RXD 에 연결, GND 공통, 9600 으로 읽으세요.")
