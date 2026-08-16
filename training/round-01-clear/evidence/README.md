# B2-1 R01 — Evidence Guide

Evidence는 Reference 코드 존재가 아니라 **실제 CLI 동작과 영구 저장**을 증명합니다.

## 권장 Evidence

1. `01-help.txt`
   - `python -m budget_app --help`
   - 주요 subcommand `--help`
2. `02-add-list.txt`
   - 대화형 add 성공 + 생성 ID
   - list 최신순 / `--limit`
3. `03-search.txt`
   - 기간/카테고리/type/q/tag 대표 조건
4. `04-update-delete.txt`
   - 정상 수정/삭제
   - 없는 ID 오류 + nonzero exit
5. `05-summary-budget.txt`
   - 총수입/총지출/잔액/TOP N
   - 예산 사용률 + 초과 경고
6. `06-category.txt`
   - add/list/remove
   - 사용 중 카테고리 삭제 차단
7. `07-import-export.txt`
   - 고정 CSV 스키마 export
   - 정상 import
   - 깨진 행 skipped 리포트
8. `08-persistence.txt`
   - 프로그램 종료/재실행 전후 동일 데이터 확인
   - `transactions/categories/budgets` 3개 파일 존재
9. `09-tests.txt`
   - `environment/verify.sh`
   - unit test 결과
10. `10-error-exit.txt`
    - 대표 잘못된 날짜/금액/ID/파일
    - stacktrace 없음
    - exit code != 0

## 데이터 안전

Evidence용 Runtime은 개인 기존 데이터와 분리한 임시 디렉터리를 권장합니다.

```bash
export B2_DATA=/tmp/codyssey-b2-1-evidence
```

## Requirement 연결

각 Evidence는 `docs/requirements-mapping.md`의 ID와 연결해 어떤 평가 요구를 증명하는지 명확히 합니다.

## CLEAR

Reference unit tests만으로 CLEAR하지 않습니다. 실제 명령, 오류 경로, 재실행 persistence까지 확인한 뒤 `✅ CLEAR`로 판정합니다.
