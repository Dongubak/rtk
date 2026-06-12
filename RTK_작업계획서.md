# RTK 다음 작업 계획서

> 작성일: 2026-06-12
> 대상: Unicore UM982(WTRTK-982, 듀얼 안테나) + NGII VRS-RTCM34 + STM32 연동
> 목적: **개활지에서 신뢰성 있는 cm급 RTK 정확도 검증** 및 Heading/STM32 통합 마무리

---

## 0. 현재까지 완료 상태 (Done)

| 항목 | 상태 |
|---|---|
| 시리얼 COM3 = 460800 (저장) | ✅ |
| RTCM 전달 + **자동 재접속**(main.py) | ✅ |
| RTK Fixed 도달 (cm급 가능 확인) | ✅ (초기 25샘플 σ 0.3cm) |
| 한국 좌표계 변환 (EPSG:5186) | ✅ accuracy_test.py |
| COM1 9600 → STM32 (GNRMC, TTL) | ✅ |
| **STM32 시간 싱크** | ✅ 완료 |

### 직전 발견 (해결할 문제)
- **현재 위치(멀티패스 심함)에서는 Fixed 가 마진 → 좌표 드리프트**
  (X축 70초간 +11cm, 심하면 36m 폭주). `RELIABILITY 1` 이 가짜/마진 Fixed 를 유지시킴.
- → **개활지 + RELIABILITY 상향**으로 재검증 필요.

---

## 1. 다음 작업 목표 (Objectives)

1. **개활지에서 RTK Fixed 가 안정적으로 유지**되는지 (드리프트 0)
2. **cm급 정확도(반복정밀도) 검증** — 세 축 모두 σ < 2cm, 추세 없음
3. (가능 시) **절대정확도 검증** — 국가기준점 위에서 참값 대비 오차 cm
4. **Heading(pose) 검증** — 듀얼 안테나 방위각 안정 출력
5. **STM32 통합 다음 단계** — 위치/heading 활용 (시간싱크는 완료)

---

## 2. 사전 준비 (Prerequisites)

- [ ] **개활지 선정**: 반경 수십 m 내 건물·벽·큰 나무 없는 곳, 하늘 트임. (옥상이면 난간·구조물에서 멀리 한가운데)
- [ ] **안정적 전원**: 듀얼 안테나는 전류 소모 큼 → 파워드 USB 허브/외부 5V 2A↑ (USB 브라운아웃 = 위성 00개 붕괴 원인)
- [ ] **안정적 인터넷**: NTRIP 보정용. 핫스팟이면 신호/데이터 확인. (끊겨도 main.py 자동 재접속됨)
- [ ] **안테나 거치 고정**: 측정 중 절대 흔들리지 않게 (삼각대/고정대)
- [ ] **RELIABILITY 상향**: 검증용은 `CONFIG RTK RELIABILITY 3 1` + `SAVECONFIG` (신뢰성 우선)
- [ ] (선택) **국가기준점 좌표 확보**: 절대정확도 검증용. accuracy_test.py 의 `REF_LAT/REF_LON` 에 입력

---

## 3. 작업 단계 (Steps)

### Phase 1 — 개활지 Fixed 재현
1. RELIABILITY 3 적용 + SAVECONFIG (아래 4장 명령)
2. `python main.py` 실행
3. 확인: 위성 **25개+**, HDOP **1.0 이하**, 보정나이 **1초**, **위성 00개 붕괴 없음**
4. Fixed 도달까지 대기 (RELIABILITY 3 이면 최대 5~10분 가능)
   - 합격: 안정적으로 `✅ RTK Fixed` 유지
   - 불합격(계속 Float/붕괴): 자리·전원 재점검 → 더 트인 곳으로

### Phase 2 — 정확도(반복정밀도) 검증
1. main.py 종료 후 `python accuracy_test.py` (안테나 완전 고정)
2. 3~5분 수집
3. **합격 기준: X / Y / H 세 축 모두 σ < 2cm, 그리고 평균이 한 방향으로 흐르지 않을 것(드리프트 0)**
   - 이번처럼 한 축이 단조 증가하면 = 마진 Fixed → 불합격, 자리 개선

### Phase 3 — 절대정확도 검증 (기준점 있을 때)
1. 좌표 아는 기준점 위에 안테나 정확히 거치
2. accuracy_test.py 의 `REF_LAT/REF_LON` 에 참값 입력
3. 출력의 **기준점 대비 수평오차(cm)** 확인 → cm급이면 절대정확도 합격

### Phase 4 — Heading(pose) 검증
1. **두 안테나 실제 간격 측정** (줄자, m 단위)
2. `CONFIG HEADING LENGTH <측정값m> <오차m>` + `SAVECONFIG` (예: `CONFIG HEADING LENGTH 0.50 0.05`)
3. heading 출력(`$GNHDT` 등) 안정적으로 나오는지, 위치+heading(pose) 동시 유효 확인

### Phase 5 — STM32 통합 다음 단계 (시간싱크 이후)
1. STM32에서 **GNRMC 파싱** (UTC 시각 + 위치) 활용
2. (선택) **PPS 신호**로 정밀 시각 동기 (수신기 PPS 핀 → STM32)
3. 위치/heading 을 응용 로직에 연동

---

## 4. 핵심 명령 (복붙용)

```bash
# 검증 모드: RELIABILITY 3 (신뢰성 우선) + 저장
#   save_reliability.py 의 값을 3 으로 바꿔 실행하거나, 터미널(460800)에서:
#   CONFIG RTK RELIABILITY 3 1
#   SAVECONFIG

python main.py             # Fixed 도달 확인 (자동 재접속 내장)
python accuracy_test.py    # cm급 정밀도 측정 (main.py 끄고 단독 실행)
```

> 운영(빠른 Fixed) vs 검증(신뢰 Fixed): **운영 1~2 / 검증 3**.

---

## 5. 합격 기준 (Definition of Done)

| 검증 | 합격 기준 |
|---|---|
| Fixed 안정성 | 위성 00개 붕괴 0회, Float↔Fixed 잦은 전환 없음 |
| 반복정밀도 | X/Y/H 세 축 σ < 2cm, **드리프트(추세) 없음** |
| 절대정확도(선택) | 기준점 대비 수평오차 < ~3cm |
| Heading | $GNHDT 안정 출력, pose(위치+방위) 동시 유효 |

---

## 6. 리스크 & 대응

| 리스크 | 징후 | 대응 |
|---|---|---|
| 멀티패스 | 위성 적음, 한 축 드리프트, Fixed 안 됨 | 더 트인 곳, 벽/구조물 회피, 그라운드플레인 |
| 가짜/마진 Fixed | Fixed인데 좌표가 흐름 | RELIABILITY 3 로 상향 (검증 시) |
| 전원 부족 | 위성 00개 순간 붕괴 | 파워드 허브/외부 전원 |
| 네트워크 끊김 | `Errno 49`, 보정 중단 | main.py 자동 재접속(완료), 인터넷 안정화 |
| 좌표계 혼동 | 값이 수백 m 어긋남 | EPSG:5186(중부), 옛 Bessel 혼용 금지 (개념정리 문서 참고) |

---

## 7. 도구 개선 백로그 (선택)

- [ ] `accuracy_test.py` 에 **드리프트 지표**(첫↔최근 평균 차이, 축별) 추가 → 마진 Fixed 자동 감지
- [ ] 측정 결과 CSV 저장 (사후 분석/그래프)
- [ ] Heading(HDT) 동시 로깅

---

## 참고 문서
- `RTK_트러블슈팅.md` — 진단/운영
- `RTK_Fixed_달성기록.md` — Fixed 달성 과정·소요시간
- `RTK_좌표계_개념정리.md` — 데이텀/투영/정밀도vs정확도
- `RTK_설정저장방법.md` — RELIABILITY 저장
