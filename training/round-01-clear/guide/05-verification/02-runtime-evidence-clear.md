# STEP 10 — 테스트, Persistence, Evidence, CLEAR

## ① 왜 하는가
Reference 코드가 존재하는 것과 실제 미션이 완료된 것은 다릅니다. 자동 테스트와 실제 CLI 재실행을 모두 확인해야 합니다.

## ② 무엇을 하는가
`verify.sh`, unit tests, 실제 프로그램 재실행, Evidence, Evaluation Q&A를 최종 확인합니다.

## ③ 알아야 할 용어
- **단위 테스트(Unit Test)** — 작은 기능 단위를 자동 검증하는 테스트입니다.
- **검증(Verification)** — 요구사항대로 구현됐는지 확인하는 과정입니다.
- **증빙 자료(Evidence)** — 실제로 요구사항을 충족했다는 증거입니다.
- **실행 환경(Runtime)** — 프로그램이 실제로 동작하는 환경입니다.

## ④ 핵심 개념
```text
Requirement
→ Implementation
→ Test / Runtime
→ Evidence
→ Evaluation
→ CLEAR
```

자동 테스트와 실제 Runtime은 서로 대체하지 않습니다.

## ⑤ 실행
먼저 자동 검증:

```bash
bash training/round-01-clear/environment/verify.sh
```

재실행 persistence 확인:

```bash
python3 -m budget_app --data-dir "$B2_DATA" list --limit 10
python3 -m budget_app --data-dir "$B2_DATA" summary --month 2026-08 --top 3
python3 -m budget_app --data-dir "$B2_DATA" category list
ls -l "$B2_DATA"
```

최종 Evidence 기준은 다음 문서를 사용합니다.

- [`../../evidence/README.md`](../../evidence/README.md)
- [`../../docs/requirements-mapping.md`](../../docs/requirements-mapping.md)
- [`../../docs/evaluation-qa.md`](../../docs/evaluation-qa.md)
- [`../../CHECKLIST.md`](../../CHECKLIST.md)

## ⑥ 명령 해설
`verify.sh`는 Python 버전, Reference 파일, AST syntax, unit tests, command help, 핵심 구조를 확인하지만 실제 학습 데이터의 모든 사용자 흐름을 대신하지는 않습니다.

실제 CLEAR 전에는 최소한 다음을 직접 확인합니다.

```text
정상 CLI
대표 오류 CLI
프로그램 재실행
transactions/categories/budgets persistence
실제 CSV import/export
Evidence
Evaluation 설명
```

## ⑦ 정상 결과
- 자동 검증: `Result: N PASS / 0 FAIL`
- 실제 재실행: 저장 데이터가 유지됨
- 오류 경로: stacktrace 없이 원인+힌트, exit code nonzero
- Evidence: Requirement와 연결 가능한 실제 출력 존재

## ⑧ 의미
기능·구조·오류·파일 persistence의 필수 요구를 자동검증과 실제 Runtime으로 교차 확인한 것입니다.

## ⑨ 오류와 해결
FAIL 한 항목만 해당 Module/STEP으로 돌아가 수정합니다. 데이터 전체 삭제나 대규모 재설계부터 하지 않습니다.

실행환경을 MAC-V에서 WIN-V로 바꾸거나 반대로 바꾸면 새 Runtime Context에서 Preflight부터 다시 수행합니다.

## ⑩ 완료 확인
- [ ] verify 0 FAIL
- [ ] 정상 명령 실제 확인
- [ ] 대표 오류 실제 확인
- [ ] 재실행 persistence
- [ ] import/export 실제 CSV
- [ ] Evidence 정리
- [ ] Evaluation Q&A 자기 말 설명
- [ ] CHECKLIST 최종 교차검증
- [ ] **✅ B2-1 CLEAR**

---

[← 이전 학습 단위](01-code-contracts.md) · [Module 05](README.md) · [전체 Beginner Guide](../../BEGINNER-GUIDE.md)
