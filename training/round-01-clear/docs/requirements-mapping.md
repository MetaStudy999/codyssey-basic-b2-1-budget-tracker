# B2-1 R01 — Requirement / Implementation / Verification / Evidence

실제 Runtime을 하지 않은 항목은 Evidence 완료로 표시하지 않습니다.

| ID | Requirement | Reference Implementation | Verification | Evidence |
|---|---|---|---|---|
| R01 | `python -m budget_app` CLI + `--help` | `reference/budget_app/cli.py`, `__main__.py` | 각 command `--help` | help 출력 |
| R02 | Transaction 필드/dataclass | `models.py` | unit test / 코드 확인 | 코드/테스트 |
| R03 | 2+ 클래스, 3+ 모듈 | models/repositories/services/cli | 구조 검토 | 파일 트리 |
| R04 | JSONL 3개 영구 저장 | repositories | 재실행 후 데이터 유지 | data 파일 + 재실행 결과 |
| R05 | 초기 파일/카테고리 처리 | `BudgetService._initialize_categories()` | 첫 실행 | category list |
| R06 | add 대화형 + ID | `prompt_add`, `add_transaction` | 실제 입력 | 저장 완료 출력 |
| R07 | list 최신순 + `--limit` + generator | `iter_jsonl_reverse`, `list_transactions` | 테스트 + 실제 명령 | list 출력 |
| R08 | search 5종 조건 + 최신순 + streaming | `search_transactions` | 테스트/실제 명령 | search 출력 |
| R09 | update 옵션 방식 + missing id | `update_transaction`, atomic repository update | 정상/오류 테스트 | 수정/오류 출력 |
| R10 | delete `--id` + missing id | `delete_transaction`, atomic rewrite | 정상/오류 테스트 | 삭제/오류 출력 |
| R11 | summary 월 총수입/지출/잔액/TOP N | `summary` | unit + CLI | summary 출력 |
| R12 | budget set + 사용률/초과 경고 | BudgetRepository/summary CLI | unit + CLI | budget/summary 출력 |
| R13 | category add/list/remove + in-use 보호 | CategoryRepository/Service | unit + CLI | category 출력 |
| R14 | import CSV 고정 스키마 | `CSV_COLUMNS`, `import_csv` | 정상/깨진 행 테스트 | imported/skipped |
| R15 | export CSV + 조건 필수 | `export_csv` | schema unit/CLI | CSV + 출력 |
| R16 | decorator 실제 적용 | `handle_cli_errors` → `main` | error test | `[오류]`, `[힌트]` |
| R17 | 오류 stacktrace 없음 + nonzero exit | decorator/argparse | error test/실제 명령 | exit code |
| R18 | type hints | 전체 Reference Python 코드 | 코드 검토 | 함수 시그니처 |
| R19 | update/delete 저장 안정성 | `write_jsonl_atomic` + `os.replace` | unit + 코드 설명 | 재작성 전후 파일 |
| R20 | stdlib only / Python 3.10+ | imports/environment | `verify.sh` | verify 결과 |
| R21 | README 실행/저장/CSV 스키마 | root/reference README | 문서 검토 | README |
| R22 | 평가 확장성 설명 | `docs/evaluation-qa.md` | 사용자 설명 | 평가 확인 |

## Runtime Evidence 원칙

Reference unit test가 통과하더라도 최종 CLEAR 전에 다음은 실제 터미널에서 확인합니다.

- 정상 명령 10개 기능군
- 대표 오류 입력과 nonzero exit
- 프로그램 재실행 후 persistence
- import/export 실제 CSV
- `--data-dir` 분리 실행
