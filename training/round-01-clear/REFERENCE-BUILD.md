# B2-1 R01 — Reference Build

## 목적

공식 Mission/Evaluation을 기준으로 **Python 표준 라이브러리만 사용하는 파일 기반 가계부 CLI의 Reference Complete Version**을 먼저 준비합니다.

Reference Build가 완료되어도 Phase C에서 실제 명령·오류 경로·영구 저장을 검증하기 전에는 B2-1을 `✅ CLEAR`로 판정하지 않습니다.

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
- update: **옵션 기반** 방식으로 고정
- list/search: 최신순 **제너레이터 스트리밍**
- update/delete: 같은 디렉터리의 임시 파일 작성 후 `os.replace()` 원자적 교체
- import/export: 공식 CSV 스키마 고정
- import 오류 행: 정상 행은 반영하고 오류 행은 건너뛴 뒤 imported/skipped와 행별 원인을 보고
- 공통 오류 처리: 데코레이터로 분리, 스택트레이스 없이 원인+힌트, 오류 exit code 2

## Reference Complete Path

1. Source/Evaluation 분석
2. Python/저장 구조 결정
3. 모델/저장소/서비스/CLI 책임 분리
4. add
5. list + reverse JSONL streaming
6. search streaming
7. update/delete atomic rewrite
8. summary
9. budget
10. category
11. import/export CSV
12. decorator/type hints/error exit codes
13. tests
14. README/Beginner Guide/Evaluation Q&A
15. Runtime 정상/오류/재실행 검증
16. Evidence 후 CLEAR

## 상태

**Reference Build 진행 중 / Mission 상태는 ⬜ NOT STARTED 유지 / Runtime 미시작**
