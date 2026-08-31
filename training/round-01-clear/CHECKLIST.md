# B2-1 Round 01 — Mission Clear Checklist

> Mission 상태는 `⬜ NOT STARTED`, `🟡 ACTIVE`, `⛔ BLOCKED`, `✅ CLEAR`만 사용합니다. **Phase A CORE READY는 Runtime PASS/CLEAR가 아닙니다.**

## 현재 상태

- Training Round: **R01 — CLEAR**
- Mission: **B2-1**
- Runtime Mission 상태: **🟡 ACTIVE — MAC-V Runtime PASS / Evaluation Gate 진행 전**
- Phase A Reference 상태: **CORE READY**
- Actual Evidence: [`evidence/2026-08-31-mac-v-runtime.md`](evidence/2026-08-31-mac-v-runtime.md)

## A. Source / Scope

- [x] `b2-1-mission.pdf` 확인
- [x] `b2-1-mission.md` 확인
- [x] `b2-1-evaluation.md` 확인
- [x] 필수/보너스 구분
- [x] JSONL/옵션 기반 update/부분 성공 import 등 Reference 설계 결정 기록

## B. Reference 구조 / 설계

- [x] Python 3.10+ 기준
- [x] 표준 라이브러리만 사용
- [x] `python -m budget_app` entry point
- [x] models/repositories/services/cli/utils/errors 3개 이상 모듈 분리
- [x] 2개 이상 클래스
- [x] `Transaction` dataclass
- [x] 함수/메서드 type hints
- [x] 공통 오류 decorator 실제 적용
- [x] `REFERENCE-STATUS.md`
- [x] Phase A 자체감사 BLOCKER/MAJOR 0

## C. 저장 정책

- [x] 내부 저장 포맷 JSONL
- [x] `transactions.jsonl`
- [x] `categories.jsonl`
- [x] `budgets.jsonl`
- [x] 기본 `./data`
- [x] `--data-dir` 지원
- [x] 저장 파일 자동 생성
- [x] 기본 카테고리 자동 생성
- [x] update/delete same-directory temp + `fsync` + `os.replace()`
- [x] 테스트에서 transactions/categories/budgets 재오픈 persistence 확인
- [x] update/delete 후 temp 잔존 없음 + 재오픈 상태 확인
- [x] Phase C 실제 프로그램 재실행 후 3파일 persistence Evidence

## D. add / list

- [x] add 대화형 구현
- [x] 날짜 검증
- [x] type 검증
- [x] 양수 amount 검증
- [x] 등록 category 검증
- [x] memo/tags 선택 필드
- [x] 고유 ID 생성
- [x] list 최신순
- [x] `--limit`
- [x] reverse JSONL generator streaming
- [x] 테스트에서 list 반환이 실제 generator인지 확인
- [x] Phase C 실제 add/list CLI

## E. search

- [x] `--from`
- [x] `--to`
- [x] `--category`
- [x] `--type`
- [x] `--q`
- [x] `--tag`
- [x] 최신순
- [x] generator streaming
- [x] 테스트에서 5종 조건 조합과 generator 계약 확인
- [x] Phase C 실제 대표 검색

## F. update / delete

- [x] update 옵션 기반 방식으로 문서에 고정
- [x] `--id`
- [x] 선택 필드 update
- [x] 없는 ID 오류
- [x] delete `--id`
- [x] 없는 ID 오류
- [x] atomic rewrite
- [x] 재오픈 후 update/delete 결과 유지 테스트
- [x] Phase C 정상/오류 CLI

## G. summary / budget

- [x] `summary --month YYYY-MM`
- [x] 총 수입/총 지출/잔액
- [x] category 지출 TOP N
- [x] `--top`
- [x] 데이터 없는 달 명시
- [x] `budget set --month --amount`
- [x] budget persistence
- [x] 예산 사용률
- [x] 예산 초과 Warning
- [x] 단위테스트로 합계/순위/120% 초과/빈 달 확인
- [x] Phase C 실제 CLI

## H. category

- [x] add/list/remove
- [x] 사용 중 category 삭제 차단
- [x] category 재오픈 persistence 테스트
- [x] Phase C 실제 CLI

## I. import / export

- [x] import `--from`
- [x] export `--out`
- [x] export `--month`
- [x] export `--from` + `--to`
- [x] 조건 없는 export 오류
- [x] CSV `date,type,category,amount,memo,tags`
- [x] UTF-8 + 헤더
- [x] 깨진 행 부분 성공 + skipped/row reason
- [x] date-range export 테스트
- [x] Phase C 실제 CSV 파일/처리건수 Evidence

## J. 오류 / CLI 계약

- [x] root `--help`
- [x] 10개 주요 command `--help`
- [x] long option `--` 규칙 검사
- [x] stacktrace 대신 `[오류]` + `[힌트]`
- [x] 정상 main return 0
- [x] AppError return 2 / argparse nonzero
- [x] invalid date/type/category/0·음수 amount 테스트
- [x] Phase C 실제 오류 exit code Evidence

> Runtime 관찰: `search --type invalid`은 argparse native validation이 처리해 usage + 허용값 + exit 2를 출력합니다. no traceback/nonzero 조건은 PASS이며, `[오류]/[힌트]` 형식과 다른 점은 MINOR UX 일관성 사항으로 기록합니다.

## K. Generator / Decorator / Type Hint

- [x] `yield` 기반 JSONL streaming 구현
- [x] list/search generator 계약 테스트
- [x] `handle_cli_errors` decorator 분리 및 실제 `main` 적용
- [x] dataclass/Repository/Service/CLI 함수에 type hints
- [x] Evaluation 설명 기준 답안
- [ ] Phase C에서 사용자가 실제 코드 위치를 근거로 자기 말 설명

## L. Verify / Documentation / Evidence

- [x] `REFERENCE-BUILD.md`
- [x] `REFERENCE-STATUS.md`
- [x] `reference/README.md`
- [x] `BEGINNER-GUIDE.md`
- [x] `docs/requirements-mapping.md`
- [x] `docs/evaluation-qa.md`
- [x] `evidence/README.md`
- [x] `environment/verify.sh`를 AST parse + unit tests + CLI/help + README/구조 검사로 보강
- [x] verify가 bytecode/cache를 남기지 않도록 설계
- [x] 실제 환경에서 `verify.sh` 0 FAIL — 46 PASS / 0 FAIL
- [x] 실제 정상 CLI Evidence
- [x] 실제 오류 CLI Evidence
- [x] 실제 persistence Evidence
- [x] 실제 import/export Evidence

## M. Evaluation 확장성

- [x] JSONL vs CSV 장단점/선택 이유
- [x] 10만 건 병목과 DB/인덱스/집계 개선 방향
- [x] 깨진 import 행 partial-success 정책과 사용자 보고
- [ ] Phase C에서 자신의 실제 구현과 결과를 근거로 설명

## N. Final CLEAR

- [ ] 공식 Mission 누락 없음 최종 확인
- [ ] 공식 Evaluation 누락 없음 최종 확인
- [x] 실제 Reference verify/test PASS
- [x] 정상 Runtime 완료
- [x] 오류 Runtime 완료
- [x] 실제 재실행 persistence 확인
- [x] 필요한 Runtime Evidence 완료
- [ ] 설명형 평가 대응 가능
- [ ] **✅ B2-1 CLEAR**
