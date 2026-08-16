from __future__ import annotations

import json
from collections.abc import Callable, Generator
from pathlib import Path

from .errors import AppError
from .models import Budget, Transaction
from .utils import iter_jsonl, iter_jsonl_reverse, write_jsonl_atomic


class TransactionRepository:
    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "transactions.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def append(self, transaction: Transaction) -> None:
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(transaction.to_dict(), ensure_ascii=False) + "\n")

    def iter_all(self) -> Generator[Transaction, None, None]:
        for raw in iter_jsonl(self.path):
            yield Transaction.from_dict(raw)

    def iter_latest(self) -> Generator[Transaction, None, None]:
        for raw in iter_jsonl_reverse(self.path):
            yield Transaction.from_dict(raw)

    def find(self, transaction_id: str) -> Transaction | None:
        for transaction in self.iter_all():
            if transaction.id == transaction_id:
                return transaction
        return None

    def next_id(self) -> str:
        max_number = 0
        for transaction in self.iter_all():
            if transaction.id.startswith("TX-"):
                try:
                    max_number = max(max_number, int(transaction.id[3:]))
                except ValueError:
                    continue
        return f"TX-{max_number + 1:06d}"

    def update(self, transaction_id: str, transform: Callable[[Transaction], Transaction]) -> Transaction:
        found: Transaction | None = None

        def records() -> Generator[dict[str, object], None, None]:
            nonlocal found
            for transaction in self.iter_all():
                if transaction.id == transaction_id:
                    transaction = transform(transaction)
                    found = transaction
                yield transaction.to_dict()

        write_jsonl_atomic(self.path, records())
        if found is None:
            raise AppError("수정할 거래를 찾을 수 없습니다.", f"id={transaction_id}가 맞는지 list로 확인하세요.")
        return found

    def delete(self, transaction_id: str) -> bool:
        deleted = False

        def records() -> Generator[dict[str, object], None, None]:
            nonlocal deleted
            for transaction in self.iter_all():
                if transaction.id == transaction_id:
                    deleted = True
                    continue
                yield transaction.to_dict()

        write_jsonl_atomic(self.path, records())
        return deleted


class CategoryRepository:
    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "categories.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def list(self) -> list[str]:
        return [str(raw["name"]) for raw in iter_jsonl(self.path)]

    def exists(self, name: str) -> bool:
        return name in self.list()

    def add(self, name: str) -> bool:
        normalized = name.strip()
        if not normalized:
            raise AppError("카테고리 이름은 비어 있을 수 없습니다.")
        if self.exists(normalized):
            return False
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"name": normalized}, ensure_ascii=False) + "\n")
        return True

    def remove(self, name: str) -> bool:
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
    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "budgets.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def get(self, month: str) -> Budget | None:
        for raw in iter_jsonl(self.path):
            if str(raw["month"]) == month:
                return Budget(month=month, amount=int(raw["amount"]))
        return None

    def set(self, budget: Budget) -> None:
        replaced = False

        def records() -> Generator[dict[str, object], None, None]:
            nonlocal replaced
            for raw in iter_jsonl(self.path):
                if str(raw["month"]) == budget.month:
                    replaced = True
                    yield budget.to_dict()
                else:
                    yield {"month": str(raw["month"]), "amount": int(raw["amount"])}
            if not replaced:
                yield budget.to_dict()

        write_jsonl_atomic(self.path, records())
