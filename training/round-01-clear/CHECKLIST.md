# B2-1 Round 01 — Mission Clear Checklist

> Mission 상태는 `⬜ NOT STARTED`, `🟡 ACTIVE`, `⛔ BLOCKED`, `✅ CLEAR`만 사용합니다. B2-1은 현재 Reference Build를 선제 준비하며 Runtime은 앞선 미션 CLEAR 순서에 맞춰 나중에 수행합니다.

## 현재 상태

- Training Round: **R01 — CLEAR**
- Mission: **B2-1**
- Mission 상태: **⬜ NOT STARTED**
- 작업 모드: **Phase A — REFERENCE BUILD**

## A. Source

- [x] `b2-1-mission.pdf` 확인
- [x] `b2-1-mission.md` 확인
- [x] `b2-1-evaluation.md` 확인
- [x] 필수/보너스 구분
- [x] Reference 설계 결정 기록

## B. Reference 구조

- [x] Python 3.10+ 기준
- [x] 표준 라이브러리만 사용하도록 설계
- [x] `python -m budget_app` 엔트리 포인트
- [x] 3개 이상 모듈 분리
- [x] 2개 이상 클래스
- [x] dataclass Transaction
- [x] 타입 힌트
- [x] 공통 오류 decorator 실제 적용
- [x] Reference unit tests 작성
- [x] `environment/verify.sh` 작성
- [ ] Reference verify 실제 실행 결과 0 FAIL

## C. 저장 정책

- [x] 내부 저장 포맷 JSONL로 고정
- [x] `transactions.jsonl`
- [x] `categories.jsonl`
- [x] `budgets.jsonl`
- [x] 기본 `./data`
- [x] `--data-dir` 지원
- [x] 저장 파일 자동 생성
- [x] 기본 카테고리 자동 생성 정책
- [x] update/delete 임시 파일 + `os.replace()` 방식
- [ ] Runtime 재실행 후 persistence 확인

## D. add / list

- [x] add 대화형 구현
- [x] 날짜 검증
- [x] type 검증
- [x] 양수 amount 검증
- [x] 등록 category 검증
- [x] memo/tags 선택 필드
- [x] 고유 ID 생성
- [x] list 최신순 구현
- [x] `--limit` 구현
- [x] reverse JSONL generator streaming 구현
- [ ] Runtime add/list 확인

## E. search

- [x] `--from`
- [x] `--to`
- [x] `--category`
- [x] `--type`
- [x] `--q`
- [x] `--tag`
- [x] 최신순
- [x] generator streaming
- [ ] Runtime 대표 조건 확인

## F. update / delete

- [x] update 옵션 기반 방식으로 문서에 고정
- [x] `--id`
- [x] 선택 필드 update
- [x] 없는 ID 오류 처리
- [x] delete `--id`
- [x] 없는 ID 오류 처리
- [x] 원자적 재작성 구조
- [ ] Runtime 정상/오류 경로 확인

## G. summary / budget

- [x] `summary --month YYYY-MM`
- [x] 총 수입
- [x] 총 지출
- [x] 잔액
- [x] category 지출 TOP N
- [x] `--top`
- [x] 데이터 없는 달 안내
- [x] `budget set --month --amount`
- [x] budget 영구 저장
- [x] summary 예산 사용률
- [x] 초과 Warning
- [ ] Runtime 확인

## H. category

- [x] add
- [x] list
- [x] remove
- [x] 사용 중 category 삭제 차단 정책
- [ ] Runtime 확인

## I. import / export

- [x] import `--from`
- [x] export `--out`
- [x] export `--month` 조건
- [x] export `--from` + `--to` 조건
- [x] 조건 없는 export 오류
- [x] CSV `date,type,category,amount,memo,tags`
- [x] UTF-8 + 헤더
- [x] broken row 부분 성공 + skipped/원인 리포트
- [ ] Runtime CSV 확인

## J. 오류 / CLI 계약

- [x] 각 명령 argparse `--help`
- [x] stacktrace 대신 원인 + 힌트 정책
- [x] 정상 main return 0
- [x] AppError return 2
- [x] argparse 오류 nonzero exit
- [ ] Runtime 대표 오류 exit code 확인

## K. Evaluation — 구조/설명

- [x] 모듈 책임 설명 문서
- [x] 클래스 책임 경계 설명 문서
- [x] generator streaming 구현/이유 설명
- [x] decorator 분리 이유 설명
- [x] type hints 이점 설명
- [x] JSONL vs CSV 장단점/선택 이유
- [x] 10만 건 병목/개선 방향
- [x] 깨진 import 행 처리 전략
- [ ] 사용자가 실제 코드/Runtime을 근거로 자기 말로 설명

## L. Documentation / Evidence

- [x] `REFERENCE-BUILD.md`
- [x] `reference/README.md`
- [x] `BEGINNER-GUIDE.md` Step 01~10
- [x] `docs/requirements-mapping.md`
- [x] `docs/evaluation-qa.md`
- [x] `evidence/README.md`
- [ ] 실제 정상 명령 Evidence
- [ ] 실제 오류 명령 Evidence
- [ ] 실제 persistence Evidence
- [ ] 실제 import/export Evidence
- [ ] verify/test 실제 결과 Evidence

## M. Final CLEAR

- [ ] 공식 Mission 누락 없음 최종 확인
- [ ] 공식 Evaluation 누락 없음 최종 확인
- [ ] Reference tests 실제 PASS
- [ ] 정상 Runtime 완료
- [ ] 오류 Runtime 완료
- [ ] 재실행 persistence 확인
- [ ] 필요한 Evidence 완료
- [ ] 설명형 평가 대응 가능
- [ ] **✅ B2-1 CLEAR**
