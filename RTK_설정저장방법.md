# RTK 설정 영구 저장 방법 (다음 세션용)

> Fixed 가 잘 되던 핵심 설정 **`RTK RELIABILITY 1`** 을 수신기에 영구 저장하는 방법.
> 이 설정은 RAM 에만 있으면 **전원을 끄는 순간 사라지고 3(엄격)으로 되돌아가** Fixed 가 안 될 수 있다.
> `SAVECONFIG` 로 한 번만 저장해두면 이후로는 영구 유지된다.

---

## 방법 A — 스크립트 (권장, 제일 간단)

장비 연결 후 한 번만 실행. **포트 이름이 바뀌어도 자동 탐지**한다.

```bash
python save_reliability.py
```

성공하면 마지막에 이렇게 나온다:
```
=== 저장 후 확인 ===
   $CONFIG,RTK,CONFIG RTK RELIABILITY 1 1*74
   $CONFIG,COM3,CONFIG COM3 460800*2E
✅ 저장 완료. 이제 전원을 껐다 켜도 RELIABILITY 1 유지됨.
```

---

## 방법 B — 수동 (직접 명령 입력 시)

CoolTerm 등 터미널을 **460800** 으로 열고, 한 줄씩 입력:

```
CONFIG RTK RELIABILITY 1 1
SAVECONFIG
CONFIG
```

- `CONFIG RTK RELIABILITY 1 1` → 응답 `response: OK` 확인
- `SAVECONFIG` → 응답 `response: OK` 확인 (이게 영구 저장)
- `CONFIG` → 출력 중 `CONFIG RTK RELIABILITY 1 1` 보이면 성공

---

## 포트 확인 (이름이 또 바뀌었을 때)

```bash
ls /dev/tty.usbserial*
```
나온 이름을 스크립트나 main.py 의 `COM` 에 맞추면 된다. (예: `/dev/tty.usbserial-XXXX`)

---

## 저장되는 것 / 이미 저장된 것

| 설정 | 상태 | 비고 |
|---|---|---|
| `COM3 460800` (시리얼 속도) | ✅ 이미 저장됨 | 다시 안 해도 됨 |
| `RTK RELIABILITY 1 1` | ⬜ **이번에 저장 필요** | `save_reliability.py` 실행 |

---

## 저장 후 최종 확인

```bash
python main.py     # 약 3분 → ✅ RTK Fixed
```

> 참고: `SAVECONFIG` 한 번이면 RELIABILITY·COM 속도 등 **현재 모든 설정**이 통째로 저장된다.
> 트레이드오프 — RELIABILITY 1 은 Fixed 가 빨라지는 대신 오확정 위험이 약간 있다.
> 더 보수적으로 가고 싶으면 나중에 `CONFIG RTK RELIABILITY 2 1` 로 올려 절충할 수 있다.
