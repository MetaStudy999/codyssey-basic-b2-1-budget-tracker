# B2-1 R01 — Reference Status

## 판정

**Phase A Reference Build: CORE READY**

**Runtime Mission: 🟡 ACTIVE — MAC-V Runtime 기능/Evidence PASS, 최신 주석 반영본 재검증 + Evaluation/CLEAR 최종 Gate 남음**

2026-08-31 MAC-V(OrbStack Ubuntu 24.04.4)에서 실제 CLI·영구 저장·오류 경로·CSV 흐름을 수행했습니다. 실제 결과는 `evidence/2026-08-31-mac-v-runtime.md`에 기록합니다.

그 이후 입문자가 Python 코드를 직접 읽으며 학습할 수 있도록 `reference/budget_app/*.py`와 `reference/tests/test_budget_app.py`에 상세 한글 주석·docstring을 추가했습니다. **업무 로직을 바꾸기 위한 변경은 아니지만 Branch HEAD가 변경되었으므로 최신 HEAD에서 `verify.sh`를 다시 실행하기 전에는 기존 46 PASS를 최신 HEAD의 PASS로 재사용하지 않습니다.**

아직 최신 HEAD 재검증, 사용자 자기 말 Evaluation, 최종 Mission/Evaluation 교차검증을 끝내지 않았으므로 `✅ B2-1 CLEAR`는 선언하지 않습니다.

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

list/search가 단순히 결과를 내는 것뿐 아니라 실제 generator 객체인지 테스트에서 확인하도록 보강했습니다.

### 3. 오류·입력 경계

날짜, type, category, 0/음수 amount, missing update/delete ID를 테스트하여 정상 경로만 통과하는 기준본을 방지했습니다.

### 4. atomic rewrite 검증

update/delete 후 임시 파일이 남지 않고 재오픈 후에도 JSONL이 정상 읽히며 수정/삭제 상태가 유지되는지 테스트합니다.

### 5. import/export 경계

- 고정 CSV header 확인
- 깨진 행 partial-success + row reason 확인
- date-range export 확인
- export 조건 누락 오류 확인

### 6. verify 부작용 감소

기존 `compileall` 대신 AST parse를 사용하여 verification 때문에 Repository에 `__pycache__`를 만들지 않도록 했습니다. Unit test도 `PYTHONDONTWRITEBYTECODE=1`로 실행하도록 했습니다.

### 7. README/CLI 계약 검사

verify가 root/subcommand `--help`, long option `--` 규칙, 3개 저장 파일, README의 실행/저장/CSV 설명을 다시 확인합니다.

### 8. 입문자 코드 주석 보강

다음 Python 파일에 기능의 목적, 계층 책임, 타입/제너레이터/데코레이터/원자적 재작성/테스트 의도를 설명하는 주석과 docstring을 추가했습니다.

- `reference/budget_app/__init__.py`
- `reference/budget_app/__main__.py`
- `reference/budget_app/cli.py`
- `reference/budget_app/errors.py`
- `reference/budget_app/models.py`
- `reference/budget_app/repositories.py`
- `reference/budget_app/services.py`
- `reference/budget_app/utils.py`
- `reference/tests/test_budget_app.py`

## Phase A 준비 완료

- [x] Mission/Evaluation 분석
- [x] 전체 기능 기준 구현
- [x] 모듈/클래스 책임 분리
- [x] generator/decorator/type hint
- [x] persistence/atomic rewrite
- [x] 정상/대표 오류 unit tests
- [x] Reference verify 기준 준비
- [x] Beginner Guide
- [x] Requirements Mapping
- [x] Evaluation Q&A
- [x] Evidence Guide
- [x] Secret 요구 없음 / Secret-pattern 검사 유지
- [x] 허위 Runtime PASS 없음
- [x] 입문자용 Python 상세 주석/docstring 반영

## Phase C Runtime 상태

- [x] 주석 보강 전 MAC-V 실제 Python 환경에서 verify 0 FAIL — **46 PASS / 0 FAIL**
- [x] 실제 대화형 add
- [x] 모든 기능군 CLI 정상 흐름
- [x] 대표 오류와 nonzero exit
- [x] 프로그램 재실행 후 transactions/categories/budgets persistence 확인
- [x] 실제 import/export CSV
- [x] 실제 malformed CSV partial-success
- [x] 실제 Runtime Evidence 기록
- [ ] **최신 주석 반영 HEAD에서 `verify.sh` 재실행 0 FAIL 확인**
- [ ] 사용자 자기 말 평가 설명
- [ ] 공식 Mission/Evaluation 최종 교차검증
- [ ] `✅ B2-1 CLEAR`

## 실제 Runtime 요약

| Gate | 상태 |
|---|---|
| MAC-V Preflight | PASS |
| 주석 보강 전 `verify.sh` | 46 PASS / 0 FAIL |
| 최신 HEAD `verify.sh` | **PENDING RE-VERIFY** |
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

## Current Gate

- BLOCKER: **0**
- MAJOR: **0**
- MINOR: **1** — argparse validation 출력 스타일 일관성
- RE-VERIFY: **필수** — 입문자 주석 반영 후 최신 HEAD에서 `verify.sh` 재실행
