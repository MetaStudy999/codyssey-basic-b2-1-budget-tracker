# B2-1 R01 — Reference Build

## 목적

공식 Mission/Evaluation을 기준으로 **Python 표준 라이브러리만 사용하는 파일 기반 가계부 CLI의 Reference Complete Version**을 준비합니다.

Reference Build가 완료되어도 Phase C에서 실제 CLI·오류 경로·재실행 persistence·Evidence를 확인하기 전에는 B2-1을 `✅ CLEAR`로 판정하지 않습니다.

## Source of Truth

1. `b2-1-mission.pdf`
2. `b2-1-mission.md`
3. `b2-1-evaluation.md`

## Reference 설계 결정

- 실행: `python -m budget_app <command>`
- Python: 3.10+
- 외부 패키지: 없음
- 내부 저장 포맷: **JSONL**
- 저장 파일: `transactions.jsonl`, `categories.jsonl`, `budgets.jsonl`
- 기본 저장 위치: `./data`, `--data-dir`로 변경 가능
- 초기 카테고리: 기본값 자동 생성 방식
- update: **옵션 기반** 방식
- list/search: 최신순 **generator streaming**
- update/delete: 같은 디렉터리 temp file + `fsync` + `os.replace()`
- import/export: 공식 CSV 스키마 고정
- import 깨진 행: 정상 행 partial success + skipped/row reason 보고
- 공통 오류 처리: decorator + 원인/힌트 + nonzero exit

## Reference Complete Path

1. Source/Evaluation 분석
2. Python/저장 구조 결정
3. 모델/저장소/서비스/CLI 책임 분리
4. add
5. list + reverse JSONL streaming
6. search 5종 조건 + streaming
7. update/delete atomic rewrite
8. summary
9. budget
10. category
11. import/export CSV
12. decorator/type hints/error exit codes
13. persistence/error/boundary unit tests
14. side-effect-light verify
15. README/Beginner Guide/Evaluation Q&A/Mapping
16. Phase C 실제 CLI + persistence + Evidence
17. CLEAR Gate

## Phase A 준비 결과

- [x] Source/Evaluation 분석
- [x] Python package/entry point
- [x] models/repositories/services/cli/utils/errors 모듈 분리
- [x] Transaction/Budget dataclass와 type hints
- [x] JSONL 3파일 persistence
- [x] add/list/search/update/delete
- [x] summary/budget/category
- [x] import/export 고정 CSV 스키마
- [x] reverse JSONL generator streaming
- [x] atomic rewrite (`fsync` + `os.replace`)
- [x] 공통 오류 decorator + nonzero error contract
- [x] transaction/category/budget 재오픈 persistence 테스트
- [x] generator 객체 테스트
- [x] invalid date/type/category/amount + missing ID 테스트
- [x] atomic rewrite 후 temp 잔존/재오픈 테스트
- [x] import partial-success + export range/조건 테스트
- [x] `environment/verify.sh` AST parse/unit/help/README/structure 검사
- [x] Root/Reference README
- [x] Beginner Guide Step 01~10
- [x] Requirement Mapping / Evaluation Q&A / Evidence Guide
- [x] `REFERENCE-STATUS.md`
- [x] 실제 Runtime 결과를 PASS로 가장하지 않음

## 자체감사 결론

Reference 구현에서 공식 평가를 가로막는 BLOCKER/MAJOR는 현재 발견되지 않았습니다. 특히 Evaluation의 핵심인 **3파일 영속성, generator streaming, decorator, type hints, atomic update/delete, import broken-row policy, nonzero error exit**를 코드와 테스트/verify에 연결했습니다.

## Phase C에서 확인할 것

- [ ] Python 3.10+ 실제 환경
- [ ] `verify.sh` 실제 0 FAIL
- [ ] 대화형 add 실제 입력
- [ ] add/list/search/update/delete 실제 CLI
- [ ] summary/budget/category 실제 CLI
- [ ] import/export 실제 CSV
- [ ] 프로그램 재실행 후 transactions/categories/budgets 실제 유지
- [ ] 대표 오류 stacktrace 없음 + exit != 0
- [ ] 실제 Evidence
- [ ] 사용자 자기 말 Evaluation 설명
- [ ] `✅ B2-1 CLEAR`

## 현재 판정

**Phase A Reference Build: CORE READY**

**Runtime Mission 상태: ⬜ NOT STARTED / CLEAR 아님**

다음 Phase A 작업은 B2-2 자체감사/정합성 마감입니다.
