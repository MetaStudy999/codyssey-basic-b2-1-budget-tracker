# Codyssey Basic B2-1 — 나만의 용돈 기입장 프로그램 만들기

## 현재 훈련 상태

- 구분: **필수 미션 (REQUIRED)**
- Round: **R01 — CLEAR**
- Mission 상태: **⬜ NOT STARTED**
- 현재 모드: **Phase A — REFERENCE BUILD**

Reference Complete Version을 먼저 준비합니다. 실제 CLI 실행·오류 경로·재실행 persistence·Evidence를 확인하기 전에는 CLEAR로 판정하지 않습니다.

## 공식 원본

- `b2-1-mission.pdf`
- `b2-1-mission.md`
- `b2-1-evaluation.md`

공식 원본은 수정하지 않습니다.

## Reference 시작 위치

- `training/round-01-clear/REFERENCE-BUILD.md`
- `training/round-01-clear/BEGINNER-GUIDE.md`
- `training/round-01-clear/CHECKLIST.md`
- `training/round-01-clear/reference/README.md`

## 기술 스택

- Python 3.10+
- Python standard library only
- argparse CLI
- dataclass / type hints
- JSONL persistence
- CSV import/export
- unittest

## 로컬 실행

Repository 루트에서:

```bash
export PYTHONPATH="$PWD/training/round-01-clear/reference"
python3 -m budget_app --help
```

별도 실습 데이터 폴더 권장:

```bash
export B2_DATA=/tmp/codyssey-b2-1-data
python3 -m budget_app --data-dir "$B2_DATA" category list
```

## 저장 파일 위치와 형식

기본 위치는 `./data`이며 `--data-dir`로 변경할 수 있습니다.

Reference 내부 저장 포맷은 JSONL입니다.

```text
data/
├── transactions.jsonl
├── categories.jsonl
└── budgets.jsonl
```

첫 실행에서 category 파일이 비어 있으면 기본 카테고리 `food`, `transport`, `rent`, `salary`, `etc`를 생성합니다.

## 주요 명령

```bash
python3 -m budget_app add
python3 -m budget_app list --limit 10
python3 -m budget_app search --from 2026-08-01 --to 2026-08-31 --category food
python3 -m budget_app summary --month 2026-08 --top 3
python3 -m budget_app budget set --month 2026-08 --amount 500000
python3 -m budget_app category add --name health
python3 -m budget_app category list
python3 -m budget_app category remove --name health
python3 -m budget_app update --id TX-000001 --amount 18000 --memo "저녁"
python3 -m budget_app delete --id TX-000001
python3 -m budget_app export --out export.csv --month 2026-08
python3 -m budget_app import --from import.csv
```

`--data-dir`을 사용할 때는 Reference CLI에서 main command 앞에 둡니다.

```bash
python3 -m budget_app --data-dir "$B2_DATA" list --limit 10
```

## update 방식

공식 허용안 중 **옵션 기반 방식**으로 고정했습니다.

```bash
python3 -m budget_app update --id TX-000001 --amount 20000 --memo "수정 메모"
```

지정하지 않은 필드는 기존 값을 유지합니다.

## CSV import/export 스키마

UTF-8, 헤더 포함:

| column | required | 설명 |
|---|---|---|
| date | Y | `YYYY-MM-DD` |
| type | Y | `income` / `expense` |
| category | Y | 등록된 category |
| amount | Y | 양수 정수 |
| memo | N | 문자열 |
| tags | N | 쉼표 구분 문자열 |

Export는 `--month YYYY-MM` 또는 `--from YYYY-MM-DD --to YYYY-MM-DD` 중 한 조건 방식이 필요합니다.

Import는 정상 행은 저장하고 깨진 행은 건너뛴 뒤 `imported`, `skipped`, 행별 오류 원인을 출력하는 부분 성공 정책을 사용합니다.

## 테스트/검증

```bash
bash training/round-01-clear/environment/verify.sh
```

또는 unit test만:

```bash
export PYTHONPATH="$PWD/training/round-01-clear/reference"
python3 -m unittest discover \
  -s training/round-01-clear/reference/tests \
  -p 'test_*.py' -v
```

## 핵심 설계

- `models.py`: 데이터 구조
- `repositories.py`: JSONL 파일 I/O
- `services.py`: 비즈니스 규칙
- `cli.py`: 사용자 명령/입출력
- `utils.py`: generator, decorator, validation, atomic rewrite

list/search는 generator streaming으로 처리하며, update/delete는 임시 파일을 완전히 쓴 뒤 `os.replace()`로 원자적 교체합니다.

## CLEAR 원칙

Reference Build만으로 CLEAR하지 않습니다. Phase C에서 정상 기능, 대표 오류, 재실행 persistence, import/export, test 결과와 Evidence를 실제로 확인한 뒤 `✅ CLEAR`로 변경합니다.
