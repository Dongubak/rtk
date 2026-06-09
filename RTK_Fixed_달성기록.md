# RTK Fixed 달성 기록

> Unicore **UM982(WTRTK-982, 듀얼 안테나)** + NGII **VRS-RTCM34** 환경에서
> RTK Float 에 머물던 문제를 끝까지 추적해 **RTK Fixed** 를 달성한 기록.
> 달성일: 2026-06-09 / 장소: 옥상(트인 곳)
> 원본 로그: [`log_fixed_achieved.txt`](log_fixed_achieved.txt)

---

## 1. 결과 요약

```
✅ RTK Fixed | 위성 27~31개 | HDOP 0.5~0.6   (안정적으로 지속, 위성 00개 붕괴 없음)
```

| 항목 | 값 |
|---|---|
| 최종 상태 | **RTK Fixed (고정해)** |
| 사용 위성 | 27~31개 |
| HDOP | 0.5~0.6 |
| **보정 시작 → 첫 Fixed 소요** | **약 185초 (≈ 3분)** |
| 보정 나이(age) | 1초 (실시간) |
| 시리얼 | COM3 @ 460800 (저장됨) |

---

## 2. Fixed 까지 걸린 시간 (단계별)

`log_fixed_achieved.txt` 기준 (GGA 2Hz → 2줄 = 1초):

| 경과 시간 | 상태 | 비고 |
|---|---|---|
| 0초 | 🔵 DGPS | 보정 적용 시작 (위성 8~14개) |
| ~50초 | 🟡 GPS only | 잠깐 강등 (위성 일시 감소) |
| ~55초 | 🔵 DGPS | 회복 |
| **~80초** | 🟠 RTK Float | 반송파 해 진입, 위성 증가 |
| ~80~185초 | 🟠 RTK Float | 모호성 수렴 진행 (약 1분 45초) |
| **~185초 (3분)** | ✅ **RTK Fixed** | 정수 모호성 확정, 이후 지속 유지 |

> 정리: **DGPS → (약 80초) → Float → (약 105초 수렴) → Fixed(약 3분)**.
> 멀티패스 환경에서는 Float 진입 후 Fixed 확정까지 1~3분 더 걸리는 게 정상이다.

---

## 3. Fixed 를 위해 한 일 (전체 과정)

문제는 **하나가 아니라 여러 단계가 겹쳐** 있었고, 아래를 순서대로 해결해야 했다.

### ① 시리얼 대역폭 부족 해소 — 115200 → 460800
- NGII VRS 보정이 순간 12KB/s 까지 → 115200(최대 11.5KB/s)으로는 부족 → 보정 적체 → Fixed 불가.
- `set_baud.py` 로 수신기 **COM3** 속도를 460800 으로 변경 + `SAVECONFIG`.
- ⚠️ 주의: USB 케이블이 꽂힌 포트는 **COM3** 였음. 처음엔 COM1 을 바꿔 헛수고했었다 → `check_config.py` 의 `CONFIG` 덤프로 실제 포트 확인.

### ② 호스트 측 병목 제거 — RTCM 전달 스레드 분리
- `main.py` 에서 보정 전달을 **별도 스레드**로 옮겨, 도착 즉시 모듈로 전달 (보정 나이 1초 달성).
- `debug.py` 는 출력이 많아 루프가 느려져 보정이 지연됨 → **Fixed 테스트는 main.py 로만** 할 것.

### ③ 위치/안테나 — 트인 옥상 + 좋은 하늘
- 낮고 막힌 곳(위성 8개/HDOP 2.3)에서는 안 됨 → **트인 옥상**(위성 27~31개/HDOP 0.5~0.6)에서 성공.
- 위성 SNR 40~48, L1/L2 동시 추적 확인.

### ④ ★ 결정타 — RTK 확정 기준 완화 (RELIABILITY 3 → 1)
- 조건이 다 좋아도(30개/HDOP 0.6) **5분 넘게 Float 에서 안 넘어감**.
- 원인: `CONFIG RTK RELIABILITY 3 1` = **가장 엄격(보수적) 모드** → 멀티패스 환경에서 좀처럼 Fixed 선언 안 함.
- **`CONFIG RTK RELIABILITY 1 1`** (가장 쉽게 확정)로 변경 → 약 3분 만에 Fixed 달성.
- 트레이드오프: 확정이 빨라지는 대신 오확정 위험이 약간 증가. (VRS 는 기준선이 0 에 가까워 위험 낮음)

### ⑤ 부수 발견 — 듀얼 안테나(heading) 구성
- 이 장비는 ANT1(위치) + ANT2(방위각, heading) **듀얼 안테나**.
- `CONFIG HEADING FIXLENGTH / LENGTH 0.00 0.00` 설정 존재.
- 듀얼 안테나 + 안테나 급전(ANTENNA POWERON)은 전류 소모가 커서, USB 전원이 빠듯하면 **위성 00개 순간 붕괴**의 원인이 될 수 있음 (전원 여유 권장).

---

## 4. ⚠️ 영구 저장 필요 (중요)

`CONFIG RTK RELIABILITY 1 1` 은 현재 **RAM 에만 적용**돼 있을 수 있다.
**전원을 껐다 켜면 다시 3(엄격)으로 돌아가** Fixed 가 또 안 될 수 있으므로, 유지하려면:

```
SAVECONFIG   # 수신기에 영구 저장 (main.py 잠깐 멈추고 1회 실행)
```

> COM3=460800 은 이미 저장돼 있음. RELIABILITY 1 만 추가로 저장하면 됨.

---

## 5. 재현 절차 (다음에 Fixed 만들기)

```bash
# 1) (최초 1회만) 수신기 설정 — 이미 적용됐다면 생략
#    - COM3 460800 저장 (set_baud.py)
#    - RTK RELIABILITY 1 1 + SAVECONFIG

# 2) 트인 곳(옥상)에 안테나 두고, 전원 여유 있게
python main.py

# 3) 약 3분 정지 대기 → ✅ RTK Fixed
```

**정상 도달 기준:** 위성 25개+ / HDOP 1.0 이하 / 보정나이 1초 → 3분 내 Fixed.
**안 되면 점검:** 위성 00개 붕괴(전원), 위성 10개 이하(위치 막힘), 보정나이 증가(대역폭/포트).

---

## 6. 관련 파일

| 파일 | 용도 |
|---|---|
| `main.py` | 운영용 (스레드 보정 전달 + 상태 모니터) |
| `set_baud.py` | 시리얼 460800 변경 (적용 완료) |
| `check_config.py` | CONFIG 덤프 (포트/설정 확인) |
| `debug.py` | RTCM 상세 진단 (Fixed 테스트엔 부적합) |
| `config_um982.py` | GNSS UNMASK + NMEA 출력 복구 |
| `log_fixed_achieved.txt` | 본 Fixed 달성 원본 로그 |
| `RTK_트러블슈팅.md` | 진단/운영 가이드 |
| `RTK_설정저장방법.md` | RELIABILITY 영구 저장 방법 |
| `save_reliability.py` | RELIABILITY 1 저장 스크립트 |
| `accuracy_test.py` | 한국 좌표계 cm급 정확도 측정 |
| `RTK_좌표계_개념정리.md` | 좌표계/데이텀/투영 개념 정리 |
| `RTK_Fixed_달성기록.md` | (이 문서) Fixed 달성 과정·소요시간 |

---

## 7. 좌표 변환 & 정확도 테스트 (한국 좌표계, cm급)

> 다음 테스트 목표: **한국 좌표계 기준 cm급 정확도 검증.**
> NMEA 경위도(WGS84)를 한국 공식 좌표계(미터)로 변환한 뒤, 정지 상태 산포를 cm로 측정한다.

### 7-1. 2단계 변환

**① NMEA 형식(ddmm.mmmm) → 십진수 도**
```
위도 3728.49542091 = 37° + 28.49542091/60 = 37.47492°N
경도 12653.21795050 = 126° + 53.21795050/60 = 126.88697°E
```

**② WGS84(경위도) → 한국 2000 TM 투영(미터)**
GPS 출력은 WGS84. 한국에서 미터로 쓰려면 **Korea 2000(GRS80) TM** 으로 투영한다. 경도대별 원점:

| 원점대 | 적용 경도 | EPSG |
|---|---|---|
| 서부 | 124~126°E | 5185 |
| **중부** | **126~128°E** | **5186** ← 현장(126.89°E) |
| 동부 | 128~130°E | 5187 |
| 동해(울릉) | 130°E~ | 5188 |
| (전국 단일 / 웹지도) | 전국 | 5179 (UTM-K) |

- 현장 경도 126.89°E → **EPSG:5186 (중부원점)** 사용.
- 옛 좌표계(Bessel, EPSG:517x)는 구 지적자료용. 신규 측량은 **Korea 2000(518x)**.
- 데이텀 WGS84 ↔ Korea 2000 차이는 cm급. NGII VRS 보정을 받은 RTK 좌표는 사실상 Korea 2000 기준에 정합.

### 7-2. 변환 코드 (pyproj)

```python
from pyproj import Transformer
tf = Transformer.from_crs("EPSG:4326", "EPSG:5186", always_xy=True)  # WGS84 → 중부원점(m)

def nmea_to_deg(v):
    d = int(v // 100)
    return d + (v - d*100) / 60

lat = nmea_to_deg(3728.49542091)    # 37.47492
lon = nmea_to_deg(12653.21795050)   # 126.88697
x, y = tf.transform(lon, lat)       # ⚠ always_xy=True → (경도, 위도) 순서!
```
- `pip install pyproj`
- 결과 x=동거(E), y=북거(N), 단위 m. 두 점 거리 = √(Δx²+Δy²).

### 7-3. 정확도(cm급) 측정 — `accuracy_test.py`

RTK Fixed 일 때만 위치를 모아 EPSG:5186 로 변환하고 **반복정밀도(scatter)** 를 cm로 출력한다.

```bash
pip install pyproj
python accuracy_test.py        # 안테나 고정, Fixed 상태로 1~2분
```
출력 예:
```
[ 30샘플] 평균 X=198765.432 Y=552314.876 H=37.214 m | 수평σ=  0.8cm (X0.6/Y0.5) 수직σ=  1.5cm
```
- **수평σ < ~1cm, 수직σ < ~2cm** 면 RTK Fixed 정상 cm급.
- 절대 정확도는 `accuracy_test.py` 의 `REF_LAT/REF_LON` 에 **측량된 기준점 참값**을 넣으면 기준점 대비 오차(cm)까지 출력.
- ⚠ 반복정밀도(σ)='흔들림', 절대정확도='참값과의 거리' — **둘은 다르다.** cm급 *절대* 검증엔 기준점 참값이 필수.

