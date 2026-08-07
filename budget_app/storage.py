from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Iterable, Iterator

from .exceptions import BudgetError
from .models import Transaction

DEFAULT_CATEGORIES = ("food", "transport", "rent", "salary", "other")


class DataPaths:
    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir
        self.transactions = data_dir / "transactions.jsonl"
        self.categories = data_dir / "categories.jsonl"
        self.budgets = data_dir / "budgets.jsonl"

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.transactions.touch(exist_ok=True)
        self.budgets.touch(exist_ok=True)
        if not self.categories.exists() or self.categories.stat().st_size == 0:
            self._write_jsonl_atomic(
                self.categories,
                ({"name": name} for name in DEFAULT_CATEGORIES),
            )

    @staticmethod
    def _write_jsonl_atomic(path: Path, rows: Iterable[dict[str, object]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                for row in rows:
                    handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass
            raise


class TransactionRepository:
    def __init__(self, paths: DataPaths) -> None:
        self.paths = paths

    def iter_transactions(self) -> Iterator[Transaction]:
        """Stream transactions one JSONL record at a time in stored newest-first order."""
        try:
            with self.paths.transactions.open("r", encoding="utf-8") as handle:
                for line_no, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        payload = json.loads(line)
                        yield Transaction.from_mapping(payload)
                    except (json.JSONDecodeError, KeyError, TypeError, BudgetError) as exc:
                        raise BudgetError(
                            f"거래 저장 파일 {line_no}번째 행을 읽을 수 없습니다.",
                            "손상된 행을 수정하거나 정상 백업으로 복구해 주세요.",
                        ) from exc
        except OSError as exc:
            raise BudgetError("거래 저장 파일을 열 수 없습니다.", str(exc)) from exc

    def _all(self) -> list[Transaction]:
        return list(self.iter_transactions())

    @staticmethod
    def _sort_key(tx: Transaction) -> tuple[str, str]:
        return (tx.date, tx.id)

    def _write_sorted(self, transactions: Iterable[Transaction]) -> None:
        ordered = sorted(transactions, key=self._sort_key, reverse=True)
        DataPaths._write_jsonl_atomic(self.paths.transactions, (tx.to_dict() for tx in ordered))

    def next_id(self) -> str:
        maximum = 0
        for tx in self.iter_transactions():
            if tx.id.startswith("TX-"):
                try:
                    maximum = max(maximum, int(tx.id[3:]))
                except ValueError:
                    continue
        return f"TX-{maximum + 1:06d}"

    def add(self, transaction: Transaction) -> None:
        rows = self._all()
        rows.append(transaction)
        self._write_sorted(rows)

    def add_many(self, transactions: Iterable[Transaction]) -> None:
        rows = self._all()
        rows.extend(transactions)
        self._write_sorted(rows)

    def find(self, transaction_id: str) -> Transaction | None:
        for tx in self.iter_transactions():
            if tx.id == transaction_id:
                return tx
        return None

    def update(self, transaction_id: str, changes: dict[str, object]) -> Transaction:
        rows = self._all()
        updated: Transaction | None = None
        rewritten: list[Transaction] = []
        for tx in rows:
            if tx.id != transaction_id:
                rewritten.append(tx)
                continue
            payload = tx.to_dict()
            payload.update(changes)
            payload["id"] = tx.id
            updated = Transaction.from_mapping(payload)
            rewritten.append(updated)
        if updated is None:
            raise BudgetError(f"거래 id를 찾을 수 없습니다: {transaction_id}", "list 또는 search로 id를 확인해 주세요.")
        self._write_sorted(rewritten)
        return updated

    def delete(self, transaction_id: str) -> None:
        rows = self._all()
        rewritten = [tx for tx in rows if tx.id != transaction_id]
        if len(rewritten) == len(rows):
            raise BudgetError(f"거래 id를 찾을 수 없습니다: {transaction_id}", "list 또는 search로 id를 확인해 주세요.")
        self._write_sorted(rewritten)


class CategoryStore:
    def __init__(self, paths: DataPaths) -> None:
        self.paths = paths

    def list(self) -> list[str]:
        categories: list[str] = []
        try:
            with self.paths.categories.open("r", encoding="utf-8") as handle:
                for line_no, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        payload = json.loads(line)
                        name = str(payload["name"]).strip()
                    except (json.JSONDecodeError, KeyError, TypeError) as exc:
                        raise BudgetError(
                            f"카테고리 저장 파일 {line_no}번째 행을 읽을 수 없습니다.",
                            "손상된 행을 수정해 주세요.",
                        ) from exc
                    if name:
                        categories.append(name)
        except OSError as exc:
            raise BudgetError("카테고리 저장 파일을 열 수 없습니다.", str(exc)) from exc
        return categories

    def add(self, name: str) -> None:
        normalized = name.strip()
        if not normalized:
            raise BudgetError("카테고리명은 비어 있을 수 없습니다.", "카테고리명을 입력해 주세요.")
        categories = self.list()
        if normalized in categories:
            raise BudgetError(f"이미 존재하는 카테고리입니다: {normalized}", "다른 이름을 사용해 주세요.")
        categories.append(normalized)
        DataPaths._write_jsonl_atomic(self.paths.categories, ({"name": item} for item in sorted(categories)))

    def remove(self, name: str) -> None:
        categories = self.list()
        if name not in categories:
            raise BudgetError(f"카테고리를 찾을 수 없습니다: {name}", "category list로 이름을 확인해 주세요.")
        remaining = [item for item in categories if item != name]
        DataPaths._write_jsonl_atomic(self.paths.categories, ({"name": item} for item in remaining))


class BudgetStore:
    def __init__(self, paths: DataPaths) -> None:
        self.paths = paths

    def _load(self) -> dict[str, int]:
        budgets: dict[str, int] = {}
        try:
            with self.paths.budgets.open("r", encoding="utf-8") as handle:
                for line_no, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        payload = json.loads(line)
                        budgets[str(payload["month"])] = int(payload["amount"])
                    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                        raise BudgetError(
                            f"예산 저장 파일 {line_no}번째 행을 읽을 수 없습니다.",
                            "손상된 행을 수정해 주세요.",
                        ) from exc
        except OSError as exc:
            raise BudgetError("예산 저장 파일을 열 수 없습니다.", str(exc)) from exc
        return budgets

    def set(self, month: str, amount: int) -> None:
        budgets = self._load()
        budgets[month] = amount
        DataPaths._write_jsonl_atomic(
            self.paths.budgets,
            ({"month": key, "amount": value} for key, value in sorted(budgets.items())),
        )

    def get(self, month: str) -> int | None:
        return self._load().get(month)
