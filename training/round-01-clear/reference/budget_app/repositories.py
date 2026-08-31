"""JSONL 저장 파일을 읽고 쓰는 Repository 계층입니다.

Repository(저장소) 계층은 '어떻게 파일에 저장할 것인가'를 책임집니다.
금액이 양수인지, 카테고리가 유효한지 같은 업무 규칙은 ``services.py``에서
처리하고, 이 파일은 거래/카테고리/예산 데이터를 실제 JSONL 파일에 보관합니다.

저장 파일
---------
- ``transactions.jsonl``: 거래
- ``categories.jsonl``: 카테고리
- ``budgets.jsonl``: 월 예산

update/delete처럼 기존 내용을 바꿔야 하는 작업은 ``utils.write_jsonl_atomic``을
사용하여 임시 파일을 완성한 뒤 ``os.replace()``로 교체합니다.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Generator
from pathlib import Path

from .errors import AppError
from .models import Budget, Transaction
from .utils import iter_jsonl, iter_jsonl_reverse, write_jsonl_atomic


class TransactionRepository:
    """거래(Transaction)를 ``transactions.jsonl``에 저장하고 조회합니다."""

    def __init__(self, data_dir: Path) -> None:
        # data_dir 아래에 거래 전용 파일 경로를 만듭니다.
        self.path = data_dir / "transactions.jsonl"

        # 부모 폴더가 없으면 생성합니다. parents=True는 중간 폴더도 함께 만들고,
        # exist_ok=True는 이미 폴더가 있어도 오류를 내지 않게 합니다.
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # 첫 실행이라 파일이 없어도 빈 JSONL 파일을 만들어 둡니다.
        self.path.touch(exist_ok=True)

    def append(self, transaction: Transaction) -> None:
        """거래 한 건을 파일 맨 뒤에 한 줄로 추가합니다."""

        # 'a'는 append 모드입니다. 기존 내용을 지우지 않고 마지막에 이어 씁니다.
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            # ensure_ascii=False를 사용하면 한글 메모를 \uXXXX 형태로 바꾸지 않고
            # 사람이 읽을 수 있는 한글 그대로 JSON에 저장합니다.
            handle.write(json.dumps(transaction.to_dict(), ensure_ascii=False) + "\n")

    def iter_all(self) -> Generator[Transaction, None, None]:
        """오래된 거래부터 한 건씩 반환하는 제너레이터입니다."""

        # iter_jsonl()이 파일 전체를 list로 만들지 않고 한 줄씩 dict를 넘겨 줍니다.
        for raw in iter_jsonl(self.path):
            yield Transaction.from_dict(raw)

    def iter_latest(self) -> Generator[Transaction, None, None]:
        """최신 거래부터 한 건씩 반환하는 제너레이터입니다."""

        # 최신순 list/search를 위해 파일 끝에서부터 읽는 제너레이터를 사용합니다.
        for raw in iter_jsonl_reverse(self.path):
            yield Transaction.from_dict(raw)

    def find(self, transaction_id: str) -> Transaction | None:
        """ID가 같은 거래를 찾고, 없으면 None을 반환합니다."""

        for transaction in self.iter_all():
            if transaction.id == transaction_id:
                return transaction
        return None

    def next_id(self) -> str:
        """기존 거래 중 가장 큰 번호 다음의 새 ID를 만듭니다.

        예: TX-000001, TX-000002가 있다면 TX-000003을 반환합니다.
        현재 Reference는 학습용 파일 구조이므로 전체 거래를 한 번 순회합니다.
        거래가 매우 많아지면 DB의 자동 증가 키 같은 방법이 더 효율적입니다.
        """

        max_number = 0
        for transaction in self.iter_all():
            if transaction.id.startswith("TX-"):
                try:
                    # 'TX-' 뒤의 숫자 부분만 int로 바꾸어 가장 큰 값을 기억합니다.
                    max_number = max(max_number, int(transaction.id[3:]))
                except ValueError:
                    # 형식이 다른 오래된 ID가 있더라도 새 ID 생성 전체를 중단하지 않습니다.
                    continue
        return f"TX-{max_number + 1:06d}"

    def update(self, transaction_id: str, transform: Callable[[Transaction], Transaction]) -> Transaction:
        """특정 ID의 거래만 변환하여 전체 JSONL을 안전하게 다시 씁니다.

        ``transform``은 기존 Transaction을 받아 수정된 Transaction을 반환하는 함수입니다.
        Repository는 어떤 필드를 어떻게 검증할지 몰라도 되고, 단지 해당 ID를 찾아
        transform을 적용한 뒤 안전하게 저장하면 됩니다.
        """

        found: Transaction | None = None

        def records() -> Generator[dict[str, object], None, None]:
            # 바깥 함수의 found 변수에 값을 저장하기 위해 nonlocal을 사용합니다.
            nonlocal found

            for transaction in self.iter_all():
                if transaction.id == transaction_id:
                    # 대상 거래에서만 Service가 전달한 변환 함수를 실행합니다.
                    transaction = transform(transaction)
                    found = transaction

                # 대상 여부와 관계없이 최종적으로 보존할 모든 거래를 한 건씩 넘깁니다.
                yield transaction.to_dict()

        # 임시 파일 작성 -> flush/fsync -> os.replace 순서로 원자적 재작성합니다.
        write_jsonl_atomic(self.path, records())

        if found is None:
            raise AppError("수정할 거래를 찾을 수 없습니다.", f"id={transaction_id}가 맞는지 list로 확인하세요.")
        return found

    def delete(self, transaction_id: str) -> bool:
        """특정 ID의 거래를 제외하고 파일을 다시 써 삭제합니다."""

        deleted = False

        def records() -> Generator[dict[str, object], None, None]:
            nonlocal deleted

            for transaction in self.iter_all():
                if transaction.id == transaction_id:
                    # 삭제 대상은 새 파일에 yield하지 않습니다.
                    deleted = True
                    continue

                # 나머지 거래만 새 파일에 기록합니다.
                yield transaction.to_dict()

        write_jsonl_atomic(self.path, records())
        return deleted


class CategoryRepository:
    """카테고리를 ``categories.jsonl``에 저장하고 조회합니다."""

    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "categories.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def list(self) -> list[str]:
        """저장된 모든 카테고리 이름을 리스트로 반환합니다."""

        return [str(raw["name"]) for raw in iter_jsonl(self.path)]

    def exists(self, name: str) -> bool:
        """같은 이름의 카테고리가 이미 있는지 확인합니다."""

        return name in self.list()

    def add(self, name: str) -> bool:
        """새 카테고리를 추가하고, 중복이면 False를 반환합니다."""

        # 앞뒤 공백을 제거해 ' food '와 'food'가 다르게 저장되는 것을 막습니다.
        normalized = name.strip()
        if not normalized:
            raise AppError("카테고리 이름은 비어 있을 수 없습니다.")
        if self.exists(normalized):
            return False

        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"name": normalized}, ensure_ascii=False) + "\n")
        return True

    def remove(self, name: str) -> bool:
        """해당 카테고리를 제외하고 파일을 원자적으로 다시 씁니다."""

        removed = False

        def records() -> Generator[dict[str, str], None, None]:
            nonlocal removed

            for raw in iter_jsonl(self.path):
                if str(raw["name"]) == name:
                    removed = True
                    continue
                yield {"name": str(raw["name"])}

        write_jsonl_atomic(self.path, records())
        return removed


class BudgetRepository:
    """월별 예산을 ``budgets.jsonl``에 저장하고 조회합니다."""

    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "budgets.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def get(self, month: str) -> Budget | None:
        """지정한 YYYY-MM 월의 예산을 찾고 없으면 None을 반환합니다."""

        for raw in iter_jsonl(self.path):
            if str(raw["month"]) == month:
                return Budget(month=month, amount=int(raw["amount"]))
        return None

    def set(self, budget: Budget) -> None:
        """같은 월이 있으면 교체하고, 없으면 파일 끝에 새 예산을 추가합니다."""

        replaced = False

        def records() -> Generator[dict[str, object], None, None]:
            nonlocal replaced

            for raw in iter_jsonl(self.path):
                if str(raw["month"]) == budget.month:
                    # 같은 월이 이미 있으면 새 금액으로 한 번 교체합니다.
                    replaced = True
                    yield budget.to_dict()
                else:
                    # 다른 월의 예산은 그대로 보존합니다.
                    yield {"month": str(raw["month"]), "amount": int(raw["amount"])}

            # 파일 전체를 확인했는데 같은 월이 없었다면 새 월 예산을 마지막에 추가합니다.
            if not replaced:
                yield budget.to_dict()

        write_jsonl_atomic(self.path, records())
