# B2-1 Reference Budget App

## 실행 환경

- Python 3.10+
- 표준 라이브러리만 사용
- 외부 `pip install` 없음

Repository 루트에서:

```bash
export PYTHONPATH="$PWD/training/round-01-clear/reference"
python -m budget_app --help
```

기본 데이터 디렉터리는 현재 작업 디렉터리의 `./data`입니다. 다른 위치를 사용하려면 **메인 명령 앞에** `--data-dir`을 둡니다.

```bash
python -m budget_app --data-dir /tmp/b2-1-data category list
```

## 내부 저장 포맷

Reference는 JSONL을 선택합니다.

```text
data/
├── transactions.jsonl
├── categories.jsonl
└── budgets.jsonl
```

JSONL 선택 이유:

- 한 줄에 한 레코드라 append가 단순함
- 거래 목록을 한 줄씩 스트리밍 가능
- Python 표준 `json` 모듈만으로 처리 가능
- CSV보다 tags 같은 구조를 안전하게 표현하기 쉬움

단점은 관계형 질의·인덱스가 없고 update/delete에 파일 재작성이 필요하다는 점입니다. Reference는 임시 파일 + `os.replace()`로 원자적 교체합니다.

## 주요 명령

```bash
python -m budget_app add
python -m budget_app list --limit 10
python -m budget_app search --from 2026-08-01 --to 2026-08-31 --category food
python -m budget_app summary --month 2026-08 --top 3
python -m budget_app budget set --month 2026-08 --amount 500000
python -m budget_app category add --name health
python -m budget_app category list
python -m budget_app category remove --name health
python -m budget_app update --id TX-000001 --amount 18000 --memo "저녁"
python -m budget_app delete --id TX-000001
python -m budget_app export --out export.csv --month 2026-08
python -m budget_app import --from import.csv
```

`update`는 **옵션 기반 방식**으로 고정했습니다. 지정하지 않은 필드는 기존 값을 유지합니다.

## CSV import/export 스키마

UTF-8, 헤더 포함:

| column | required | 설명 |
|---|---|---|
| date | Y | `YYYY-MM-DD` |
| type | Y | `income` / `expense` |
| category | Y | 등록된 카테고리 |
| amount | Y | 양수 정수 |
| memo | N | 문자열 |
| tags | N | 쉼표 구분 문자열 |

Import는 깨진 행이 있으면 정상 행은 반영하고 잘못된 행은 건너뛴 뒤 `imported`, `skipped`, 행별 원인을 출력합니다.

## 초기 카테고리

첫 실행에서 카테고리 파일이 비어 있으면 다음 기본값을 자동 생성합니다.

- food
- transport
- rent
- salary
- etc

## 테스트

```bash
export PYTHONPATH="$PWD/training/round-01-clear/reference"
python -m unittest discover \
  -s training/round-01-clear/reference/tests \
  -p 'test_*.py' -v
```

## 저장 안정성

`update`와 `delete`, budget/category 재작성은 같은 디렉터리에 임시 JSONL 파일을 완전히 쓴 뒤 `os.replace()`로 교체합니다. 중간에 기존 파일을 직접 잘라내지 않는 구조입니다.

## 10만 건으로 커질 경우

현재 파일 기반 구조의 주요 병목은 ID 탐색, update/delete 전체 재작성, summary 전체 순회입니다. 대규모 데이터 단계에서는 SQLite/PostgreSQL 같은 DB, 인덱스, 집계 캐시/증분 집계를 검토합니다. B2-1에서는 공식 요구사항인 파일 기반 저장과 제너레이터 스트리밍 학습을 우선합니다.
