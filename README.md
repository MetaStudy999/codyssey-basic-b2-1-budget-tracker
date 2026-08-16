# Codyssey Basic B2-1 — 나만의 용돈 기입장 프로그램 만들기

## 현재 훈련 상태

- 구분: **필수 미션 (REQUIRED)**
- Round: **R01 — CLEAR**
- Runtime Mission 상태: **⬜ NOT STARTED**
- Phase A Reference 상태: **CORE READY**

Reference Complete Version과 자체감사를 준비했습니다. 실제 CLI 실행·오류 경로·재실행 persistence·Evidence를 확인하기 전에는 CLEAR로 판정하지 않습니다.

## 공식 원본

- `b2-1-mission.pdf`
- `b2-1-mission.md`
- `b2-1-evaluation.md`

공식 원본은 수정하지 않습니다.

## Reference 시작 위치

- `training/round-01-clear/REFERENCE-STATUS.md` — Phase A 자체감사 결과
- `training/round-01-clear/REFERENCE-BUILD.md` — 기준 구현/검증 설계
- `training/round-01-clear/BEGINNER-GUIDE.md` — Phase C 단계별 실습
- `training/round-01-clear/CHECKLIST.md` — Mission/Evaluation/CLEAR Gate
- `training/round-01-clear/reference/README.md` — Reference 앱 사용법

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

기본 위치는 `./data`이며 `--data-dir`로 변경할 수 있습니다. Reference 내부 저장 포맷은 JSONL입니다.

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

`--data-dir`은 main command 앞에 둡니다.

```bash
python3 -m budget_app --data-dir "$B2_DATA" list --limit 10
```

## update 방식

공식 허용안 중 **옵션 기반 방식**으로 고정했습니다. 지정하지 않은 필드는 기존 값을 유지합니다.

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

Import는 정상 행은 저장하고 깨진 행은 건너뛴 뒤 `imported`, `skipped`, 행별 원인을 출력하는 부분 성공 정책을 사용합니다.

## Reference 자체감사에서 보강한 항목

- transactions/categories/budgets **3종 재오픈 persistence 테스트**
- list/search 실제 generator 객체 확인
- 날짜/type/category/0·음수 amount 검증
- missing update/delete ID 오류
- atomic rewrite 뒤 temp 잔존 여부와 재오픈 결과
- import broken-row/row reason, export date range/조건 검사
- verify가 `compileall` 대신 AST parse를 사용하여 Repository에 bytecode cache를 만들지 않음
- root/subcommand help, long option `--`, README/저장 구조를 자동 점검

## 테스트/검증

```bash
bash training/round-01-clear/environment/verify.sh
```

또는 unit test만:

```bash
export PYTHONPATH="$PWD/training/round-01-clear/reference"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
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

**Phase A: CORE READY**

**Runtime: ⬜ NOT STARTED / CLEAR 아님**

Phase C에서 정상 기능, 대표 오류, 재실행 persistence, import/export, test 결과와 Evidence를 실제로 확인한 뒤에만 `✅ CLEAR`로 변경합니다.
