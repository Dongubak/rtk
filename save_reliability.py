"""
RTK 확정 기준(RELIABILITY)을 1로 설정하고 수신기에 영구 저장(SAVECONFIG).

다음에 장비 연결한 뒤 한 번만 실행하면 됨. 포트 이름이 바뀌어도 자동 탐지한다.
(COM3=460800 은 이미 저장돼 있으므로, 이 스크립트는 RELIABILITY 만 저장한다.)

    python save_reliability.py
"""
import serial, time, glob, sys

BPS = 460800   # 이미 저장된 수신기 속도

# 1) 포트 자동 탐지
ports = glob.glob('/dev/tty.usbserial*')
if not ports:
    print("❌ USB 시리얼 포트가 없습니다. 케이블/전원 연결을 확인하세요.")
    sys.exit(1)
COM = ports[0]
print(f"포트 탐지: {COM} @ {BPS}\n")

ser = serial.Serial(COM, BPS, timeout=1)
time.sleep(0.4); ser.reset_input_buffer()


def send(cmd, wait=0.8, show=("response", "RELIABILITY", "SAVECONFIG", "COM3")):
    ser.reset_input_buffer()
    ser.write((cmd + "\r\n").encode())
    time.sleep(wait)
    out = []
    while ser.in_waiting:
        l = ser.readline().decode("ascii", errors="ignore").strip()
        if l and any(k in l for k in show):
            out.append(l)
    return out


# 2) 저장 전 현재값
print("=== 저장 전 ===")
for l in send("CONFIG", wait=1.2):
    if "RELIABILITY" in l and "RTK" in l:
        print("  ", l)

# 3) RELIABILITY 1 설정
print("\n>>> CONFIG RTK RELIABILITY 1 1")
for l in send("CONFIG RTK RELIABILITY 1 1"):
    if "response" in l:
        print("  ", l)

# 4) 영구 저장
print("\n>>> SAVECONFIG")
for l in send("SAVECONFIG", wait=1.2):
    print("  ", l)

# 5) 저장 후 확인
print("\n=== 저장 후 확인 ===")
ok = False
for l in send("CONFIG", wait=1.2):
    if "RELIABILITY" in l and "RTK" in l:
        print("  ", l)
        if "RELIABILITY 1" in l:
            ok = True
    if "COM3" in l:
        print("  ", l)

ser.close()
print("\n✅ 저장 완료. 이제 전원을 껐다 켜도 RELIABILITY 1 유지됨." if ok
      else "\n⚠️ 확인 실패 — 다시 실행하거나 응답 로그를 확인하세요.")
