# codyssey-basic-b2-1-budget-tracker

B2-1 **나만의 용돈 기입장 프로그램 만들기**의 Python 3.10+ 표준 라이브러리 구현입니다.

## 실행

```bash
python -m budget_app --help
python -m budget_app --data-dir ./data category list
```

`--data-dir`를 생략하면 `./data`를 사용합니다. 처음 실행하면 다음 세 영속 파일이 자동 생성됩니다.

```text
data/
├── transactions.jsonl
├── categories.jsonl
└── budgets.jsonl
```

카테고리가 비어 있으면 `food`, `transport`, `rent`, `salary`, `other`를 자동 생성합니다.

## 주요 명령

### 거래 추가(add) — 대화형 고정

```bash
python -m budget_app add
```

날짜, 타입, 카테고리, 금액, 메모, 태그를 순서대로 입력합니다. 성공 시 `TX-000001` 형태의 id를 출력합니다.

### 목록 / 검색

```bash
python -m budget_app list --limit 20
python -m budget_app search --from 2026-08-01 --to 2026-08-31 --category food --type expense --q lunch --tag meal
```

`transactions.jsonl`은 최신 날짜 순으로 유지되며 `list/search`는 `yield` 기반 제너레이터로 파일을 한 행씩 순회합니다. `list --limit`은 필요한 개수만 읽고 중단합니다.

### 수정 / 삭제

B2-1의 `update` 방식은 **옵션 기반**으로 고정했습니다.

```bash
python -m budget_app update --id TX-000001 --amount 18000 --memo "점심+커피"
python -m budget_app delete --id TX-000001
```

수정/삭제는 전체 결과를 임시 파일에 쓴 뒤 `os.replace()`로 원자 교체합니다. 존재하지 않는 id는 사용자 오류 메시지와 non-zero exit code로 처리합니다.

### 카테고리 / 예산

```bash
python -m budget_app category add --name study
python -m budget_app category list
python -m budget_app category remove --name study
python -m budget_app budget set --month 2026-08 --amount 500000
python -m budget_app summary --month 2026-08 --top 3
```

거래가 사용 중인 카테고리는 삭제하지 않습니다. `summary`는 총수입/총지출/잔액, 카테고리별 지출 TOP N, 예산 사용률과 초과 경고를 출력합니다.

## CSV import / export

고정 교환 스키마는 다음과 같습니다.

| column | required | 설명 |
|---|:---:|---|
| `date` | Y | `YYYY-MM-DD` |
| `type` | Y | `income` / `expense` |
| `category` | Y | 등록된 카테고리 |
| `amount` | Y | 양수 정수 |
| `memo` | N | 문자열 |
| `tags` | N | 쉼표 구분 문자열 |

공통 규칙은 **UTF-8 + 헤더 포함**입니다.

```bash
python -m budget_app export --out export.csv --month 2026-08
python -m budget_app export --out export.csv --from 2026-08-01 --to 2026-08-31
python -m budget_app import --from export.csv
```

Import는 사용자 신뢰와 데이터 안전을 위해 **전체 검증 후 전체 반영(rollback 정책)** 을 사용합니다. 한 행이라도 잘못되면 import 전체를 취소하고 기존 거래 파일을 변경하지 않으며, 문제 행 번호와 해결 힌트를 출력합니다.

## 오류 처리 / 종료 코드

`@cli_guard` 데코레이터가 공통 CLI 오류 경계를 담당합니다. 예상 가능한 입력·파일 오류는 Python traceback 대신 다음 형식으로 출력됩니다.

```text
[오류] 원인
[힌트] 해결 방법
```

정상 종료는 `0`, 애플리케이션 오류는 `2` 등 non-zero code를 반환합니다.

## 구조와 책임

```text
budget_app/
├── __main__.py      # module entry point
├── cli.py           # argparse, 대화형 입력, 출력
├── models.py        # Transaction dataclass, 검증, tags 파싱
├── storage.py       # JSONL 파일 I/O, generator, atomic rewrite
├── services.py      # 기능 규칙, 검색/요약, CSV import/export
├── decorators.py    # 공통 CLI 예외 처리 decorator
└── exceptions.py    # 사용자에게 안전하게 노출 가능한 오류 타입
```

주요 클래스는 `Transaction`, `TransactionRepository`, `CategoryStore`, `BudgetStore`, `BudgetService`입니다. CLI 출력 책임, 서비스 규칙, 저장 책임을 분리해 평가 시 각 책임 경계를 설명할 수 있도록 했습니다.

## 왜 JSONL인가

애플리케이션 저장 포맷으로 JSONL을 선택했습니다.

- 장점: 한 줄이 한 레코드라 generator로 순차 읽기 쉽고, `tags` 같은 리스트를 자연스럽게 보존하며, 표준 `json`만으로 처리할 수 있습니다.
- 단점: CSV보다 사람이 표 형태로 보기 어렵고, id 검색/update/delete는 인덱스가 없어 O(n) 스캔이 필요합니다.
- CSV는 외부 교환 포맷으로 사용해 Excel/스프레드시트 호환성과 Mission의 고정 스키마 요구를 충족합니다.

## 10만 건으로 증가할 때의 병목과 개선

현재 구조의 주 병목은 다음입니다.

1. id 생성이 최대 id를 찾기 위해 O(n) 순회합니다.
2. add/update/delete/import가 최신순 보장을 위해 파일 전체를 재작성할 수 있습니다.
3. summary는 월 인덱스가 없어 O(n) 순회합니다.

B2-1 필수 범위를 넘지 않는 선에서 현재는 generator로 **조회 메모리 사용량**을 제한합니다. 10만 건 이상을 운영 수준으로 확장한다면 id 메타데이터 분리, 월 단위 파티셔닝, append journal + compaction, 또는 상위 미션에서 데이터베이스/인덱스 도입을 검토할 수 있습니다.

## 테스트

외부 패키지 없이 실행합니다.

```bash
python -m unittest discover -s tests -v
```

검증 범위: add/list/search/summary/export/import/update/delete, category, budget, 3파일 persistence, generator 경로, CSV UTF-8/header/schema round-trip, malformed import rollback, 잘못된 입력/없는 id의 non-zero exit code와 traceback 비노출.

## 공식 문서 / Workcell

- [B2-1 미션](./b2-1-mission.md)
- [B2-1 평가 문항](./b2-1-evaluation.md)
- [MISSION-WORK-PACKET.md](./MISSION-WORK-PACKET.md)
