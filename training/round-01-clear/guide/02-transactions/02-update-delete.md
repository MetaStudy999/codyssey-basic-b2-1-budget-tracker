# STEP 05 — update/delete와 원자적 파일 교체

## ① 왜 하는가
파일 기반 저장은 수정·삭제 중 중단되면 데이터가 손상될 수 있습니다. 공식 미션은 안정적인 전체 재작성, 임시 파일, 원자적 교체를 고려하도록 요구합니다.

## ② 무엇을 하는가
옵션 기반 update와 ID 기반 delete를 실행하고 존재하지 않는 ID 오류도 확인합니다.

## ③ 알아야 할 용어
- **원자적 교체(Atomic Replace)** — 최종 교체가 한 시점에 일어나도록 파일을 바꾸는 방식입니다.
- **임시 파일(Temporary File)** — 기존 파일 대신 새 내용을 먼저 완성하는 보조 파일입니다.
- **fsync** — 운영체제 버퍼에 있는 데이터를 디스크 반영 대상으로 밀어내는 호출입니다.

## ④ 핵심 개념
```mermaid
flowchart LR
    A[기존 JSONL] --> B[임시 파일 전체 작성] --> C[flush/fsync] --> D[os.replace]
```

기존 파일을 먼저 비우지 않고 새 파일을 완성한 뒤 교체합니다.

## ⑤ 실행
먼저 list에서 실제 ID를 확인한 뒤:

```bash
python3 -m budget_app --data-dir "$B2_DATA" list --limit 10
python3 -m budget_app --data-dir "$B2_DATA" update --id TX-000001 --amount 18000 --memo "저녁"
python3 -m budget_app --data-dir "$B2_DATA" list --limit 10
python3 -m budget_app --data-dir "$B2_DATA" delete --id TX-000001
python3 -m budget_app --data-dir "$B2_DATA" delete --id TX-999999; echo "exit=$?"
```

## ⑥ 명령 해설
Reference의 update는 **옵션 기반 방식**으로 고정되어 있습니다. 지정하지 않은 필드는 기존 값을 유지하며, 없는 ID를 성공으로 숨기지 않습니다.

## ⑦ 정상 결과
정상 ID는 수정·삭제되고, 없는 ID는 `[오류]`, `[힌트]`, `exit=2`가 확인됩니다.

## ⑧ 의미
CRUD의 Update/Delete, 오류 계약, 파일 재작성 안정성을 함께 확인한 것입니다.

## ⑨ 오류와 해결
- 수정 옵션을 하나도 주지 않음 → 최소 한 필드를 지정합니다.
- category를 없는 값으로 변경 → 먼저 `category add`를 실행합니다.
- 실제 ID가 다름 → `list`로 다시 확인합니다.

## ⑩ 완료 확인
- [ ] 옵션 기반 update
- [ ] delete
- [ ] 없는 ID 오류
- [ ] nonzero exit
- [ ] 원자적 교체 구조 설명 가능

---

[← 이전 학습 단위](01-add-list-search.md) · [Module 02](README.md) · [다음 Module →](../03-analysis-rules/README.md)
