# RTK Float → Fixed 트러블슈팅 & 운영 가이드

> Unicore **UM982 (WTRTK-982)** + NGII **VRS-RTCM34** NTRIP 환경에서
> RTK Float 에서 Fixed 로 넘어가지 않는 문제를 진단·해결한 기록과 운영 절차.
> 최종 갱신: 2026-06-08

---

## 1. 현재 확정된 설정 (Quick Reference)

| 항목 | 값 |
|---|---|
| 수신기 | Unicore UM982 (WTRTK-982) |
| USB-시리얼 경로 (macOS) | `/dev/tty.usbserial-130` |
| 수신기 내부 포트 | **COM3** (USB 케이블이 연결된 포트) |
| **시리얼 속도(BPS)** | **460800** ← 수신기에 SAVECONFIG 로 저장됨 |
| NTRIP 서버 | `RTS1.ngii.go.kr:2101` |
| 마운트포인트 | `VRS-RTCM34` (GPS+GLO+GAL+BDS+QZS 5종) |
| 계정 | user `hyuk6578` / pwd `ngii` |
| 안테나 | 이중대역(multiband), 금속 테이블(그라운드플레인) 위 |

> ⚠️ `main.py` / `debug.py` / `config_um982.py` 의 `BPS` 는 모두 **460800** 이어야 함.
> 115200 으로 되돌리면 보정 데이터 대역폭 부족으로 RTK 가 다시 안 됨 (아래 2-A 참고).

---

## 2. 무엇이 문제였나 (진단 요약)

Float→Fixed 실패는 **두 단계의 원인**이 겹쳐 있었다.

### 2-A. 시리얼 대역폭 부족 (해결됨 ✅)

`debug.py` 로 측정한 보정 데이터량:

```
RTCM 수신량 = 약 120,726 bytes / 10초 ≈ 12.1 KB/s
115200 baud = 115200 ÷ 10(8N1) = 11,520 bytes/s = 11.5 KB/s  ← 물리적 최대치
```

**보정(12.1KB/s) > 시리얼 한계(11.5KB/s)** 라서 NTRIP 으로 받은 RTCM 을
수신기로 다 못 넘김 → 보정신호 나이(age)가 계속 증가 → 수신기가 "오래된
보정"으로 판단 → Fixed 진입 불가, Float→DGPS→GPS 로 왕복 강등.

**해결:**
1. 수신기 COM3 속도를 **460800** 으로 올림 (`set_baud.py` → `CONFIG COM3 460800` + `SAVECONFIG`). 460800 은 46KB/s 라 4배 여유.
2. `main.py` 에서 **RTCM 전달을 별도 스레드로 분리** (도착 즉시 모듈로 전달, 호스트 측 지연 제거).

### 2-B. 멀티패스 (남은 과제 ❌)

대역폭을 고친 뒤에는 **위성 22개 / HDOP 0.7 / RTK Float 도달**까지 정상 확인.
그러나 Fixed 로는 못 넘어가고 다음 증상이 나타남:

- 약 7초 단위로 **위성 수가 0개, HDOP 9999 로 순간 끊김** (체크섬 정상 = 진짜 수신기 출력)
- Float 해의 **높이가 실제보다 ~80m 어긋남** (해가 떠돎)

이는 **주변 큰 건물 외벽 반사(멀티패스)** 로 반송파 위상이 오염된 전형적 증상.
반송파 위상이 수십 초~수 분 연속 추적돼야 정수 모호성(ambiguity)이 풀려 Fixed
가 되는데, 멀티패스로 추적이 자꾸 끊겨 모호성 해결이 매번 리셋됨.

**대응 (물리 영역):**
1. 안테나를 건물 외벽에서 **최대한 멀리, 옥상 가장 트인 곳/높은 곳**으로 이동.
2. **파워드 USB 허브/외부 전원** 으로 교체 (USB 직접 급전 시 RTK 연산 부하에서 LNA 브라운아웃 → 위성 끊김 유발 가능).
3. 재배치 후 **움직이지 말고 3~5분** 정지 (수신기 RTK TIMEOUT 600초 동안 계속 시도).

---

## 3. 실행 방법

### 평상시 운영 — `main.py`

```bash
python main.py
```

- RTCM 전달(스레드) + 상태 모니터링. **Fixed 도달 확인은 이걸로.**
- 출력 예:
  ```
  상태: ✅ RTK Fixed | 위성 18개 | HDOP 0.8
  ```
- fix 코드: `0`=No Fix, `1`=GPS only, `2`=DGPS, `4`=RTK Fixed, `5`=RTK Float

### 보정 데이터 상세 진단 — `debug.py`

```bash
python debug.py
```

- RTCM 메시지 타입별 카운트, throughput, NMEA 종류를 출력.
- **주의:** 모든 줄을 출력하느라 루프가 느려져 보정 전달이 throttle 될 수 있음.
  메시지 종류/대역폭 점검용으로만 사용하고, **Fixed 테스트는 main.py 로** 할 것.

### 수신기 설정 확인 — `check_config.py`

```bash
python check_config.py     # BPS=460800 으로 접속해 CONFIG 덤프
```

- 각 COM 포트의 baud, 활성 설정을 확인. `CONFIG COM3 460800` 이 보이면 정상.

### 시리얼 속도 변경 — `set_baud.py` (이미 적용 완료)

```bash
python set_baud.py
```

- COM3 baud 를 460800 으로 변경 → 새 속도로 재접속 검증 → `SAVECONFIG`.
- 실패 시 자동으로 230400 폴백. **이미 460800 으로 저장돼 있으므로 재실행 불필요.**

### GNSS/NMEA 출력 복구 — `config_um982.py`

```bash
python config_um982.py
```

- MASK 로 비활성화된 GNSS 재활성화 + 통합 NMEA(GN/GP/GL/GA/GB) 출력 설정 복구.

---

## 4. 문제 해결 체크리스트

증상별로 위에서부터 확인.

### Fixed 가 전혀 안 되고 GPS↔DGPS↔Float 를 왕복한다
- [ ] `debug.py` 로 RTCM throughput 확인. **시리얼 BPS 가 대역폭보다 작지 않은지** (2-A).
- [ ] 모든 스크립트 BPS 가 460800 인지, `check_config.py` 로 COM3=460800 인지.
- [ ] NTRIP 응답이 `ICY 200 OK` 인지 (계정/마운트포인트).

### Float 까지는 가는데 Fixed 로 못 넘어간다
- [ ] **위성 0개 / HDOP 9999 순간 끊김**이 있는지 → 있으면 멀티패스/전원 (2-B).
- [ ] 안테나가 건물 외벽·구조물에서 떨어진 트인 곳인지.
- [ ] 전원이 충분한지 (파워드 허브로 교체 테스트).
- [ ] 이중대역 이상 안테나인지 (단일대역은 Fixed 사실상 불가).
- [ ] 재배치 후 3~5분 정지 대기했는지.

### NMEA 가 깨져 보이거나(`? (205)` 등) 출력이 멈춘다
- [ ] 터미널/스크립트의 baud 가 수신기 baud(460800)와 일치하는지.
  (불일치하면 깨진 글자로 보이거나 출력이 멈춘 것처럼 보임 — 고장 아님.)
- [ ] 백그라운드 실행 시 출력이 안 보이면 `python -u` (unbuffered) 로 실행.

### 위성군 일부($GL/$GA/$GB 등)가 안 나온다
- [ ] `config_um982.py` 실행해 UNMASK + NMEA 출력 복구.

---

## 5. 핵심 수치 (정상 기준)

| 지표 | 정상 범위 |
|---|---|
| 사용 위성 수 | 15개 이상 (5종이면 20+도 가능) |
| HDOP | 1.0 이하면 양호 |
| RTCM throughput | 약 10~13 KB/s (VRS-RTCM34 기준) |
| Float→Fixed 소요 | 좋은 환경 10~60초, 멀티패스 환경은 수 분 |
| 시리얼 BPS | 460800 (보정량 대비 4배 여유) |

---

## 6. 파일 목록

| 파일 | 용도 |
|---|---|
| `main.py` | **운영용.** NTRIP→RTCM 전달(스레드) + RTK 상태 모니터링 |
| `debug.py` | RTCM 메시지/대역폭 상세 진단 |
| `check_config.py` | 수신기 CONFIG 덤프 (포트별 baud 확인) |
| `set_baud.py` | 시리얼 속도 변경(460800)+저장 (적용 완료) |
| `config_um982.py` | GNSS UNMASK + NMEA 출력 복구 |
| `RTK_입문가이드.md` | RTK 개념/입문 가이드 |
| `RTK_트러블슈팅.md` | (이 문서) 진단 기록 + 운영 절차 |
