"""
WTRTK-982 (Unicore UM982) 설정 복구 + 정상 NMEA 출력
"""
import serial
import time

COM = '/dev/tty.usbserial-130'   # 실제 포트로 맞출 것
BPS = 460800                     # set_baud.py 실행 후 (이전: 115200)

COMMANDS = [
    # 1. 잘못된 MASK 해제 — 모든 GNSS 다시 활성화
    "UNMASK GPS",
    "UNMASK GLO",
    "UNMASK GAL",
    "UNMASK BDS",
    "UNMASK QZSS",

    # 2. 기존 출력 정리
    "UNLOGALL COM1",

    # 3. 다중 GNSS 통합 NMEA 출력
    "LOG GNGGA ONTIME 1",     # 통합 GGA (모든 위성군의 위성 수 포함)
    "LOG GNRMC ONTIME 1",     # 통합 RMC
    "LOG GNGSA ONTIME 1",     # 통합 GSA
    "LOG GNVTG ONTIME 1",     # 통합 VTG
    "LOG GPGSV ONTIME 1",     # 통합 GSV (모든 위성군의 신호 강도)

    # 4. 확인용 — 현재 상태 출력
    "CONFIG",

    # 5. 영구 저장
    "SAVECONFIG",
]

ser = serial.Serial(COM, BPS, timeout=1)
print(f"UM982 연결: {COM} @ {BPS}\n")
print("⚠️  이전 설정에서 MASK로 GNSS가 비활성화된 상태를 복구합니다...\n")

for cmd in COMMANDS:
    print(f">>> {cmd}")
    ser.write((cmd + "\r\n").encode())
    time.sleep(0.5)
    while ser.in_waiting:
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if line:
            # 응답 확인 강조
            if "response: OK" in line:
                print(f"    ✅ {line}")
            elif "FAIL" in line or "ERROR" in line:
                print(f"    ❌ {line}")
            else:
                print(f"    {line}")
    print()

print("✅ 복구 완료. debug.py로 NMEA에 $GN/$GL/$GA/$GB가 나오는지 확인하세요.")
ser.close()
