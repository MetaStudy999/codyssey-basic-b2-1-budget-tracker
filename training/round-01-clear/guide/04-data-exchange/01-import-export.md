# STEP 08 — CSV import/export

## ① 왜 하는가
공식 미션은 외부 파일에서 거래를 가져오고 조건에 맞는 거래를 CSV로 내보내는 기능을 요구합니다.

## ② 무엇을 하는가
공식 최소 CSV 스키마로 export하고 다시 import하며 일부 잘못된 행 처리도 확인합니다.

## ③ 알아야 할 용어
- **CSV(Comma-Separated Values)** — 표 형태 데이터를 텍스트로 교환하는 형식입니다.
- **스키마(Schema)** — 파일이 가져야 할 컬럼과 데이터 규칙입니다.
- **부분 성공(Partial Success)** — 정상 행은 처리하고 잘못된 행은 별도 보고하는 정책입니다.

## ④ 핵심 개념
공식 CSV 컬럼은 다음 6개이며 UTF-8, 헤더 포함입니다.

```text
date,type,category,amount,memo,tags
```

내부 저장은 JSONL, 외부 교환은 CSV로 역할을 분리합니다.

## ⑤ 실행
```bash
python3 -m budget_app --data-dir "$B2_DATA" export --out /tmp/b2-1-export.csv --month 2026-08
head -n 5 /tmp/b2-1-export.csv

export B2_IMPORT=/tmp/codyssey-b2-1-imported
rm -rf "$B2_IMPORT"
python3 -m budget_app --data-dir "$B2_IMPORT" import --from /tmp/b2-1-export.csv
python3 -m budget_app --data-dir "$B2_IMPORT" list --limit 20
```

조건 없는 export 오류도 확인합니다.

```bash
python3 -m budget_app --data-dir "$B2_DATA" export --out /tmp/no-condition.csv; echo "exit=$?"
```

깨진 행을 직접 확인하려면 별도 CSV를 만들되 개인 데이터가 아닌 가상 데이터만 사용합니다.

## ⑥ 명령 해설
- Export는 `--month` 또는 `--from` + `--to` 조건이 필요합니다.
- Import는 잘못된 행을 `skipped`로 보고해 전체 성공으로 오해하지 않게 합니다.
- 정상 행과 오류 행의 처리 결과를 분리해서 출력합니다.

## ⑦ 정상 결과
CSV 헤더와 컬럼이 공식 스키마와 같고 import 후 거래가 생성됩니다. 잘못된 행은 행 번호와 원인이 표시됩니다.

## ⑧ 의미
내부 JSONL 저장과 외부 CSV 교환을 분리하면서 정해진 계약으로 데이터를 주고받을 수 있습니다.

## ⑨ 오류와 해결
- CSV 필수 컬럼 누락 → 헤더를 공식 스키마에 맞춥니다.
- 등록되지 않은 category → category를 먼저 등록하거나 CSV를 수정합니다.
- export 조건 누락 → `--month` 또는 `--from`/`--to`를 지정합니다.

## ⑩ 완료 확인
- [ ] export 조건
- [ ] UTF-8 header
- [ ] 6개 CSV 컬럼
- [ ] import
- [ ] broken row report
- [ ] 오류 exit code 확인

---

[← Module 04](README.md) · [전체 Beginner Guide](../../BEGINNER-GUIDE.md) · [다음 Module →](../05-verification/README.md)
