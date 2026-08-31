# B2-1 R01 — MAC-V Runtime Evidence (2026-08-31)

> 이 문서는 2026-08-31 실제 MAC-V(OrbStack Ubuntu) 터미널에서 수행하고 사용자 출력으로 확인한 결과만 기록합니다. 실행하지 않은 항목을 PASS로 만들지 않습니다.

## 1. Runtime Context

| 항목 | 실제 결과 |
|---|---|
| Runtime | MAC-V — OrbStack Ubuntu |
| OS | Ubuntu 24.04.4 LTS |
| Architecture | x86_64 |
| Python | 3.12.3 |
| Git | 2.43.0 |
| Repository | `MetaStudy999/codyssey-basic-b2-1-budget-tracker` |
| Branch | `mission/b2-1-r01-clear` |
| 시작 Commit | `6e8c16e` |
| Runtime data | `/tmp/codyssey-b2-1-r01-data` |

Repository는 Runtime 데이터와 분리했고 각 단계 후 `git status --short`가 비어 있음을 확인했습니다.

## 2. Automated Verification

실행:

```bash
bash training/round-01-clear/environment/verify.sh
```

실제 결과:

```text
Result: 46 PASS / 0 FAIL
VERIFY_EXIT=0
```

확인 항목에는 Python 3.10+, 필수 파일, AST syntax, dataclass, generator/yield, decorator, atomic replace, unit tests, root/subcommand help, `--` long option convention, README 계약, 3개 persistent store, Secret-pattern 파일 부재가 포함되었습니다.

**판정: PASS**

## 3. Storage Initialization

첫 Runtime에서 `category list` 실행 후 다음 3개 파일을 실제 확인했습니다.

```text
transactions.jsonl : 0 lines
categories.jsonl   : 5 lines
budgets.jsonl      : 0 lines
CATEGORY_EXIT=0
```

초기 카테고리:

```text
food
transport
rent
salary
etc
```

**판정: PASS**

## 4. Add / List / Transaction Persistence

실제 저장된 거래:

```text
TX-000002 | 2026-08-31 | income  | salary | 100000 | 수입 [income,test]
TX-000001 | 2026-08-31 | expense | food   | 15000  | 점심 식사 [meal,lunch]
```

`list --limit 1`은 `TX-000002`만 출력했고, `list --limit 10`은 최신순으로 `TX-000002 → TX-000001`을 출력했습니다.

`transactions.jsonl`은 2줄이었고 새로운 Python 프로세스로 다시 실행한 뒤에도 같은 2건이 유지되었습니다.

**판정: PASS — Transaction persistence 확인**

## 5. Search

실제 확인한 조건:

| 조건 | 실제 결과 |
|---|---|
| `--from 2026-08-01 --to 2026-08-31` | 2건 |
| `--category food` | TX-000001 |
| `--type income` | TX-000002 |
| `--q 점심` | TX-000001 |
| `--tag lunch` | TX-000001 |
| 5조건 복합 검색 | TX-000001 |
| `--category rent` | `[안내] 조건에 맞는 거래가 없습니다.` |

**판정: PASS**

## 6. Update / Delete / Atomic Rewrite Runtime

### Missing ID 오류 경로

```text
[오류] 수정할 거래를 찾을 수 없습니다.
[힌트] id=TX-000003가 맞는지 list로 확인하세요.
UPDATE_EXIT=2

[오류] 삭제할 거래를 찾을 수 없습니다.
[힌트] id=TX-000003가 맞는지 list로 확인하세요.
DELETE_EXIT=2
```

### 정상 Update

임시 거래 `TX-000003`을 생성한 뒤 실제 값을 변경했습니다.

```text
BEFORE: amount=2500, memo=수정된 임시 거래, tags=[temp,updated]
AFTER : amount=3000, memo=최종 수정 테스트, tags=[temp,updated,final]
UPDATE_EXIT=0
```

파일 hash도 실제 변경되었습니다.

```text
BEFORE_HASH=7705ef225ab5110be3e816843b8d34f6a627ff7d800ae2863bb7a48130af775b
AFTER_HASH=4382c8dfe804a481aa4006968f85d7cd3a88ba388b4e302cf3a5035956d61f7b
```

### 정상 Delete

```text
[삭제 완료] id=TX-000003
DELETE_EXIT=0
TX-000003_NOT_FOUND
```

삭제 전후 hash도 달랐습니다.

```text
BEFORE_HASH=4382c8dfe804a481aa4006968f85d7cd3a88ba388b4e302cf3a5035956d61f7b
AFTER_HASH=42bf645621ef93a3cac1c6f58a7afc7d797dfea32a745a6dea0a1c2148f44647
```

삭제 후 새 Python 프로세스에서도 `TX-000003`은 다시 나타나지 않았고, atomic rewrite용 임시 파일 잔존도 없었습니다.

**판정: PASS**

## 7. Summary / Budget / Budget Persistence

설정:

```text
2026-08 budget = 10000
BUDGET_EXIT=0
```

실제 summary:

```text
총 수입: 100000원
총 지출: 15000원
잔액: 85000원
예산: 10000원 (사용률 150.0%)
[WARNING] 월 예산을 초과했습니다.
지출 TOP 3
1) food 15000원
SUMMARY_EXIT=0
```

빈 월:

```text
[안내] 2099-01 데이터 없음
```

`budgets.jsonl`은 1줄이었고 새 Python 프로세스에서도 같은 예산과 사용률이 유지되었습니다.

**판정: PASS — Budget persistence 확인**

## 8. Category Runtime

```text
health 추가 → ADD_CATEGORY_EXIT=0
health 삭제 → REMOVE_CATEGORY_EXIT=0
```

사용 중인 `food` 삭제 시도:

```text
[오류] 사용 중인 카테고리는 삭제할 수 없습니다: food
[힌트] 해당 거래의 카테고리를 먼저 update한 뒤 다시 삭제하세요.
IN_USE_EXIT=2
```

최종 category는 `food`, `transport`, `rent`, `salary`, `etc` 5개로 유지되었습니다.

**판정: PASS**

## 9. CSV Export / Import

Export:

```text
[완료] /tmp/codyssey-b2-1-r01-export.csv (2 records)
EXPORT_EXIT=0
```

실제 header:

```text
date,type,category,amount,memo,tags
```

CSV는 header 포함 3줄이었습니다.

새 데이터 디렉터리 `/tmp/codyssey-b2-1-r01-import`로 Import:

```text
[완료] imported=2, skipped=0
IMPORT_EXIT=0
```

새 저장소에서 2건 거래와 `transactions.jsonl`, `categories.jsonl`, `budgets.jsonl`을 확인했습니다.

CSV는 ID를 포함하지 않으므로 Import에서 새로운 ID가 부여되지만 날짜/type/category/amount/memo/tags가 보존됨을 확인했습니다.

**판정: PASS**

## 10. Malformed CSV — Partial Success

한 행의 amount를 `-5000`으로 만든 CSV를 Import했습니다.

실제 결과:

```text
[완료] imported=2, skipped=1
[SKIP] row 3: 금액은 0보다 커야 합니다.
IMPORT_EXIT=0
```

저장된 거래는 정상 2건뿐이었고:

```text
INVALID_ROW_NOT_STORED
```

를 확인했습니다.

정책: **Partial Success** — 정상 행은 저장하고 잘못된 행은 `skipped`와 행 번호/원인을 보고합니다.

**판정: PASS**

## 11. Error / Exit Contract

실제 대표 오류:

```text
INVALID DATE
[오류] 존재하지 않는 날짜입니다.
[힌트] 실제 달력에 존재하는 YYYY-MM-DD 날짜를 입력하세요.
DATE_EXIT=2

INVALID TYPE
python -m budget_app search: error: argument --type: invalid choice: 'invalid' (choose from 'income', 'expense')
TYPE_EXIT=2

NONEXISTENT CATEGORY
[오류] 삭제할 카테고리를 찾을 수 없습니다.
[힌트] 입력값과 사용법을 확인해 주세요.
CATEGORY_EXIT=2

INVALID BUDGET AMOUNT
[오류] 예산은 0보다 커야 합니다.
[힌트] 양의 정수를 입력하세요.
AMOUNT_EXIT=2
```

모든 대표 오류에서 nonzero exit를 확인했고 Python traceback은 노출되지 않았습니다.

`--type invalid`은 application decorator가 아니라 argparse의 native validation이 처리하므로 `[오류]/[힌트]` 형식 대신 usage + 허용값 안내를 출력합니다. 기능 검증, 원인/허용값 안내, nonzero exit, no traceback 조건은 충족하지만 출력 스타일은 다른 오류와 다릅니다.

오류 실행 후에도 정상 데이터는 그대로 유지되었습니다.

**판정: PASS (argparse 출력 스타일 차이는 MINOR UX 일관성 사항)**

## 12. Requirement / Evaluation Coverage

이번 MAC-V Runtime으로 실제 확인한 항목:

- CLI 및 10개 기능군
- JSONL 3-file initialization
- add/list/latest/limit
- search 5종 및 복합 검색
- update/delete 정상·오류 경로
- file rewrite 실제 hash 변경과 delete persistence
- summary / budget / over-budget warning / empty month
- category add/list/remove / in-use protection
- fixed CSV export/import
- malformed CSV partial success
- representative errors / nonzero exit / no traceback
- transaction and budget persistence
- isolated `--data-dir`
- Repository worktree clean

## 13. Current Gate

```text
Automated verify          PASS — 46 PASS / 0 FAIL
MAC-V Runtime             PASS
Normal CLI flow           PASS
Error CLI flow            PASS
Persistence               PASS
Import / Export           PASS
Runtime Evidence          RECORDED
User own-language Eval    PENDING
Final Mission/Eval audit  PENDING
B2-1 CLEAR                NOT YET
```

`✅ B2-1 CLEAR`는 사용자 자기 말 평가 설명과 최종 Mission/Evaluation 교차검증 후에만 선언합니다.
