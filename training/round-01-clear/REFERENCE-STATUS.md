# B2-1 R01 — Reference Status

## 판정

**Phase A Reference Build: CORE READY**

**Runtime Mission: ⬜ NOT STARTED / CLEAR 아님**

이 판정은 실제 사용자 CLI 수행·영구 저장·오류 Evidence가 완료되었다는 의미가 아닙니다. 공식 Mission/Evaluation을 수행할 기준 코드, 테스트, 학습자료, 검증계획이 Phase A에서 준비되었다는 의미입니다.

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

## Phase A 준비 완료

- [x] Mission/Evaluation 분석
- [x] 전체 기능 기준 구현
- [x] 모듈/클래스 책임 분리
- [x] generator/decorator/type hint
- [x] persistence/atomic rewrite
- [x] 정상/대표 오류 unit tests
- [x] Reference verify
- [x] Beginner Guide
- [x] Requirements Mapping
- [x] Evaluation Q&A
- [x] Evidence Guide
- [x] Secret 요구 없음 / Secret-pattern 검사 유지
- [x] 허위 Runtime PASS 없음

## Phase C에서만 PASS 처리

- [ ] 실제 Python 환경에서 verify 0 FAIL
- [ ] 실제 대화형 add
- [ ] 모든 기능군 CLI 정상 흐름
- [ ] 대표 오류와 nonzero exit
- [ ] 프로그램 재실행 후 transactions/categories/budgets 유지
- [ ] 실제 import/export CSV
- [ ] 실제 Evidence
- [ ] 사용자 자기 말 평가 설명
- [ ] `✅ B2-1 CLEAR`

## Phase A Gate

- BLOCKER: **0**
- MAJOR: **0**
- Runtime-required: **분리 완료**
- False Runtime PASS: **없음**

따라서 B2-1을 Phase A 기준 **CORE READY**로 분류합니다.
