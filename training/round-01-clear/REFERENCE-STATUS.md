# B2-1 R01 — Reference Status

## 판정

**Phase A Reference Build: CORE READY**

**Runtime Mission: 🟡 ACTIVE — MAC-V Runtime + 최신 주석 반영 HEAD 재검증 PASS / Evaluation·최종 CLEAR Gate 남음**

2026-08-31 MAC-V(OrbStack Ubuntu 24.04.4 LTS, x86_64, Python 3.12.3)에서 실제 CLI·영구 저장·오류 경로·CSV 흐름을 수행했습니다.

실제 Runtime Evidence:

- `evidence/2026-08-31-mac-v-runtime.md`
- `evidence/2026-08-31-commented-head-reverify.md`

입문자가 Python 코드를 직접 읽으며 학습할 수 있도록 `reference/budget_app/*.py`와 `reference/tests/test_budget_app.py`에 상세 한글 주석·docstring을 추가한 뒤, 최신 주석 반영 HEAD `2893e82`에서도 실제 MAC-V 재검증을 수행했습니다.

```text
Result: 46 PASS / 0 FAIL
VERIFY_EXIT=0
```

따라서 **주석 보강 후 최신 검증 대상 HEAD에서도 Reference 기능 기준 PASS를 확인**했습니다.

아직 사용자 자기 말 Evaluation과 공식 Mission/Evaluation 최종 교차검증을 끝내지 않았으므로 `✅ B2-1 CLEAR`는 선언하지 않습니다.

## Source of Truth

- `b2-1-mission.pdf`
- `b2-1-mission.md`
- `b2-1-evaluation.md`

## Reference 핵심 구현

- Python 3.10+ / 표준 라이브러리 only
- `python -m budget_app`
- `models / repositories / services / cli / utils / errors` 역할 분리
- JSONL 3파일 영구 저장
- add/list/search/summary/budget/category/update/delete/import/export
- list/search generator streaming
- update/delete same-directory temp + `fsync` + `os.replace()`
- fixed CSV import/export schema
- expected error decorator + nonzero exit
- dataclass/type hints
- 입문자용 상세 코드 주석/docstring

## 자체감사에서 확인·보완한 사항

### 1. 실제 3종 persistence 검증 강화

테스트에서 transactions뿐 아니라 category와 budget도 `BudgetService`를 다시 열어 값이 유지되는지 확인하도록 보강했습니다.

### 2. streaming 계약 검증

list/search가 실제 generator 객체인지 테스트에서 확인합니다.

### 3. 오류·입력 경계

날짜, type, category, 0/음수 amount, missing update/delete ID를 테스트합니다.

### 4. atomic rewrite 검증

update/delete 후 임시 파일이 남지 않고 재오픈 후에도 JSONL이 정상 읽히며 수정/삭제 상태가 유지되는지 확인합니다.

### 5. import/export 경계

- 고정 CSV header
- 깨진 행 partial-success + row reason
- date-range export
- export 조건 누락 오류

### 6. verify 부작용 감소

AST parse와 `PYTHONDONTWRITEBYTECODE=1`을 사용해 검증 과정 자체가 불필요한 bytecode/cache를 남기지 않도록 했습니다.

### 7. README/CLI 계약 검사

verify가 root/subcommand `--help`, long option `--` 규칙, 3개 저장 파일, README 실행/저장/CSV 설명을 확인합니다.

### 8. 입문자 코드 주석 보강

다음 Python 파일에 기능 목적, 계층 책임, Python 문법, B2-1 요구 연결을 설명하는 상세 한글 주석/docstring을 추가했습니다.

- `reference/budget_app/__init__.py`
- `reference/budget_app/__main__.py`
- `reference/budget_app/cli.py`
- `reference/budget_app/errors.py`
- `reference/budget_app/models.py`
- `reference/budget_app/repositories.py`
- `reference/budget_app/services.py`
- `reference/budget_app/utils.py`
- `reference/tests/test_budget_app.py`

## Phase C Runtime 상태

- [x] MAC-V Preflight
- [x] 실제 Python 환경 `verify.sh` 0 FAIL — **46 PASS / 0 FAIL**
- [x] 실제 대화형 add
- [x] 모든 기능군 CLI 정상 흐름
- [x] 대표 오류와 nonzero exit
- [x] 프로그램 재실행 후 transactions/categories/budgets persistence 확인
- [x] 실제 import/export CSV
- [x] malformed CSV partial-success
- [x] 실제 Runtime Evidence 기록
- [x] 입문자 상세 주석 반영 후 최신 HEAD 재검증 — **46 PASS / 0 FAIL**
- [ ] 사용자 자기 말 평가 설명
- [ ] 공식 Mission/Evaluation 최종 교차검증
- [ ] `✅ B2-1 CLEAR`

## 실제 Runtime 요약

| Gate | 상태 |
|---|---|
| MAC-V Preflight | PASS |
| 주석 보강 전 Runtime | PASS |
| 최신 주석 반영 HEAD `verify.sh` | **46 PASS / 0 FAIL** |
| add/list/search | PASS |
| update/delete 정상·오류 | PASS |
| summary/budget/category | PASS |
| import/export | PASS |
| malformed CSV | PASS |
| error/nonzero exit/no traceback | PASS |
| persistence | PASS |
| Runtime Evidence | RECORDED |
| User Evaluation | PENDING |
| Final CLEAR | PENDING |

### MINOR 관찰

`search --type invalid`은 argparse native validation이 처리해 `[오류]/[힌트]` 형식 대신 usage와 허용 선택값을 표시합니다. `exit=2`, 원인/허용값 안내, no traceback은 충족하므로 Runtime blocker로 보지 않지만 출력 스타일 일관성 관점에서는 MINOR입니다.

### Local Worktree 관찰

사용자 MAC-V 로컬에서 다음 untracked 경로가 확인되었습니다.

```text
?? training/round-01-clear/reference/data/
```

Git에 추적된 변경은 아니며 검증 PASS에는 영향을 주지 않았습니다. 최종 merge 전에는 내용 확인 후 실습용 생성 데이터라면 제거해 clean working tree로 정리합니다.

## Current Gate

- BLOCKER: **0**
- MAJOR: **0**
- MINOR: **1** — argparse validation 출력 스타일 일관성
- 최신 주석 반영 HEAD 재검증: **PASS — 46 PASS / 0 FAIL**
- 남은 Gate: **User Evaluation + Final Mission/Evaluation cross-check**
