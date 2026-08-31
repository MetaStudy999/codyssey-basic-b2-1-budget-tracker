# STEP 07 — category 관리와 참조 무결성

## ① 왜 하는가
거래가 사용하는 category를 무작정 삭제하면 데이터 의미가 깨질 수 있습니다.

## ② 무엇을 하는가
카테고리를 추가·조회·삭제하고 사용 중인 카테고리는 삭제가 차단되는지 확인합니다.

## ③ 알아야 할 용어
- **참조 무결성(Referential Integrity)** — 어떤 데이터가 참조하는 대상이 유효하게 유지되도록 하는 원칙입니다.

## ④ 핵심 개념
```mermaid
flowchart LR
    A[Transaction.category] --> B[Category]
    B -->|사용 중| C[삭제 차단]
```

파일 기반 프로그램에서도 관계형 DB와 비슷하게 참조 대상의 유효성을 지켜야 합니다.

## ⑤ 실행
```bash
python3 -m budget_app --data-dir "$B2_DATA" category add --name health
python3 -m budget_app --data-dir "$B2_DATA" category list
python3 -m budget_app --data-dir "$B2_DATA" category remove --name health
```

사용 중인 카테고리 삭제 오류도 확인합니다.

```bash
python3 -m budget_app --data-dir "$B2_DATA" category remove --name food; echo "exit=$?"
```

## ⑥ 명령 해설
Reference는 사용 중인 category 삭제를 막는 정책을 선택했습니다. 필요하면 먼저 해당 거래를 다른 category로 update합니다.

## ⑦ 정상 결과
사용하지 않는 category는 삭제되고, 사용 중인 category는 오류와 해결 힌트를 출력합니다.

## ⑧ 의미
파일 저장에서도 데이터 사이의 규칙을 서비스 계층이 보호합니다.

## ⑨ 오류와 해결
이미 존재하는 카테고리는 중복 추가하지 않고 안내합니다.

## ⑩ 완료 확인
- [ ] add
- [ ] list
- [ ] remove
- [ ] in-use 보호

---

[← 이전 학습 단위](01-summary-budget.md) · [Module 03](README.md) · [다음 Module →](../04-data-exchange/README.md)
