"""
UM982 현재 설정(CONFIG)을 덤프해서 어느 COM 포트에 연결돼 있는지 확인.
115200 에서 실행. 출력 전체를 복사해서 보내줄 것.
"""
import serial
import time

# COM = '/dev/tty.usbserial-130'   # 실제 포트로 맞출 것
# COM = '/dev/tty.usbserial-2130'
# COM = '/dev/tty.usbserial-21420'
COM = '/dev/tty.usbserial-21430'
BPS = 460800

ser = serial.Serial(COM, BPS, timeout=1)
time.sleep(0.5)
ser.reset_input_buffer()

# 전체 설정 출력 요청
print(">>> CONFIG\n")
ser.write(b"CONFIG\r\n")
time.sleep(1.5)

print("===== CONFIG 응답 =====")
while ser.in_waiting:
    line = ser.readline().decode("ascii", errors="ignore").strip()
    # 설정 라인(CONFIG/COM/LOG)만 보기 (NMEA 잡음 제거)
    if line and ("CONFIG" in line or "COM" in line or "LOG" in line):
        print(line)

ser.close()
print("=======================")
print("위 출력 전체를 복사해서 보내주세요.")
