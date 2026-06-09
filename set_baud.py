"""
UM982 시리얼 속도(baud)를 115200 → 460800 으로 변경 + 영구 저장.

115200 에서는 보정 데이터(약 12KB/s)가 링크 최대치(11.5KB/s)를 초과해
RTK Fixed 가 불가능하다. 한 번만 실행하면 SAVECONFIG 로 영구 반영된다.

실행 후 main.py / debug.py / config_um982.py 의 BPS 를 460800 으로 맞춰 사용할 것.
"""
import serial
import time

# COM      = '/dev/tty.usbserial-130'   # 실제 포트로 맞출 것
# COM = '/dev/tty.usbserial-2130'
COM = '/dev/tty.usbserial-21420'
OLD_BPS  = 115200
NEW_BPS  = 460800


def drain(ser, tag):
    time.sleep(0.4)
    while ser.in_waiting:
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if line:
            print(f"    [{tag}] {line}")


# 1) 현재 속도(115200)로 접속해서 속도 변경 명령 전송
print(f"접속: {COM} @ {OLD_BPS}")
ser = serial.Serial(COM, OLD_BPS, timeout=1)
time.sleep(0.5)

print(f">>> CONFIG COM3 {NEW_BPS}")
ser.write(f"CONFIG COM3 {NEW_BPS}\r\n".encode())
drain(ser, "old")        # 이 시점부터 수신기는 460800 으로 전환됨
ser.close()

# 2) 새 속도(460800)로 재접속해서 저장
time.sleep(0.5)
print(f"\n재접속: {COM} @ {NEW_BPS}")
ser = serial.Serial(COM, NEW_BPS, timeout=1)
time.sleep(0.5)

print(">>> SAVECONFIG")
ser.write("SAVECONFIG\r\n".encode())
drain(ser, "new")

print(">>> CONFIG       (확인)")
ser.write("CONFIG\r\n".encode())
drain(ser, "new")

ser.close()
print(f"\n✅ 완료. 이제 모든 스크립트의 BPS 를 {NEW_BPS} 로 두고 사용하세요.")
