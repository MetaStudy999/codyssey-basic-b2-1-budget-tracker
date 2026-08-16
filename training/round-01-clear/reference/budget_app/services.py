from __future__ import annotations

import csv
from collections import defaultdict
from collections.abc import Generator
from dataclasses import replace
from pathlib import Path
from typing import Any

from .errors import AppError
from .models import Budget, ImportResult, Transaction
from .repositories import BudgetRepository, CategoryRepository, TransactionRepository
from .utils import parse_tags, positive_int, validate_date, validate_month, validate_type

DEFAULT_CATEGORIES = ("food", "transport", "rent", "salary", "etc")
CSV_COLUMNS = ("date", "type", "category", "amount", "memo", "tags")


class BudgetService:
    """Business rules for transactions, categories, budgets and CSV I/O."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.transactions = TransactionRepository(data_dir)
        self.categories = CategoryRepository(data_dir)
        self.budgets = BudgetRepository(data_dir)
        self._initialize_categories()

    def _initialize_categories(self) -> None:
        if self.categories.list():
            return
        for name in DEFAULT_CATEGORIES:
            self.categories.add(name)

    def _require_category(self, name: str) -> str:
        normalized = name.strip()
        if not self.categories.exists(normalized):
            raise AppError(
                f"등록되지 않은 카테고리입니다: {normalized}",
                "category list로 확인하거나 category add로 먼저 등록하세요.",
            )
        return normalized

    def add_transaction(
        self,
        *,
        date: str,
        type: str,
        category: str,
        amount: str | int,
        memo: str = "",
        tags: str | list[str] | None = None,
    ) -> Transaction:
        transaction = Transaction(
            id=self.transactions.next_id(),
            type=validate_type(type),
            date=validate_date(date),
            amount=positive_int(amount),
            category=self._require_category(category),
            memo=memo.strip(),
            tags=parse_tags(tags),
        )
        self.transactions.append(transaction)
        return transaction

    def list_transactions(self, limit: int = 20) -> Generator[Transaction, None, None]:
        if limit <= 0:
            raise AppError("--limit은 1 이상이어야 합니다.")
        count = 0
        for transaction in self.transactions.iter_latest():
            yield transaction
            count += 1
            if count >= limit:
                return

    def search_transactions(
        self,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        category: str | None = None,
        type: str | None = None,
        query: str | None = None,
        tag: str | None = None,
    ) -> Generator[Transaction, None, None]:
        if date_from:
            date_from = validate_date(date_from)
        if date_to:
            date_to = validate_date(date_to)
        if date_from and date_to and date_from > date_to:
            raise AppError("--from 날짜가 --to 날짜보다 늦습니다.")
        if category:
            category = self._require_category(category)
        if type:
            type = validate_type(type)

        normalized_query = query.lower() if query else None
        normalized_tag = tag.strip() if tag else None

        for transaction in self.transactions.iter_latest():
            if date_from and transaction.date < date_from:
                continue
            if date_to and transaction.date > date_to:
                continue
            if category and transaction.category != category:
                continue
            if type and transaction.type != type:
                continue
            if normalized_query and normalized_query not in transaction.memo.lower():
                continue
            if normalized_tag and normalized_tag not in transaction.tags:
                continue
            yield transaction

    def update_transaction(
        self,
        transaction_id: str,
        *,
        date: str | None = None,
        type: str | None = None,
        category: str | None = None,
        amount: str | int | None = None,
        memo: str | None = None,
        tags: str | list[str] | None = None,
    ) -> Transaction:
        if all(value is None for value in (date, type, category, amount, memo, tags)):
            raise AppError("수정할 필드를 하나 이상 지정해야 합니다.")

        def transform(current: Transaction) -> Transaction:
            return replace(
                current,
                date=validate_date(date) if date is not None else current.date,
                type=validate_type(type) if type is not None else current.type,
                category=self._require_category(category) if category is not None else current.category,
                amount=positive_int(amount) if amount is not None else current.amount,
                memo=memo.strip() if memo is not None else current.memo,
                tags=parse_tags(tags) if tags is not None else current.tags,
            )

        return self.transactions.update(transaction_id, transform)

    def delete_transaction(self, transaction_id: str) -> None:
        if not self.transactions.delete(transaction_id):
            raise AppError("삭제할 거래를 찾을 수 없습니다.", f"id={transaction_id}가 맞는지 list로 확인하세요.")

    def summary(self, month: str, top: int = 3) -> dict[str, Any]:
        month = validate_month(month)
        if top <= 0:
            raise AppError("--top은 1 이상이어야 합니다.")

        income = 0
        expense = 0
        expense_by_category: dict[str, int] = defaultdict(int)
        count = 0

        for transaction in self.transactions.iter_all():
            if not transaction.date.startswith(month + "-"):
                continue
            count += 1
            if transaction.type == "income":
                income += transaction.amount
            else:
                expense += transaction.amount
                expense_by_category[transaction.category] += transaction.amount

        ranking = sorted(expense_by_category.items(), key=lambda item: (-item[1], item[0]))[:top]
        budget = self.budgets.get(month)
        usage = (expense / budget.amount * 100.0) if budget and budget.amount > 0 else None

        return {
            "month": month,
            "count": count,
            "income": income,
            "expense": expense,
            "balance": income - expense,
            "top": ranking,
            "budget": budget.amount if budget else None,
            "budget_usage": usage,
            "over_budget": bool(budget and expense > budget.amount),
        }

    def set_budget(self, month: str, amount: str | int) -> Budget:
        budget = Budget(month=validate_month(month), amount=positive_int(amount, "예산"))
        self.budgets.set(budget)
        return budget

    def list_categories(self) -> list[str]:
        return self.categories.list()

    def add_category(self, name: str) -> bool:
        return self.categories.add(name)

    def remove_category(self, name: str) -> None:
        normalized = name.strip()
        for transaction in self.transactions.iter_all():
            if transaction.category == normalized:
                raise AppError(
                    f"사용 중인 카테고리는 삭제할 수 없습니다: {normalized}",
                    "해당 거래의 카테고리를 먼저 update한 뒤 다시 삭제하세요.",
                )
        if not self.categories.remove(normalized):
            raise AppError("삭제할 카테고리를 찾을 수 없습니다.")

    def import_csv(self, source: Path) -> ImportResult:
        if not source.exists():
            raise AppError(f"가져올 CSV 파일이 없습니다: {source}")

        result = ImportResult()
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise AppError("CSV 헤더가 없습니다.")
            missing = [name for name in CSV_COLUMNS if name not in reader.fieldnames]
            if missing:
                raise AppError("CSV 필수 컬럼이 없습니다: " + ", ".join(missing))

            for row_no, row in enumerate(reader, start=2):
                try:
                    self.add_transaction(
                        date=row.get("date") or "",
                        type=row.get("type") or "",
                        category=row.get("category") or "",
                        amount=row.get("amount") or "",
                        memo=row.get("memo") or "",
                        tags=row.get("tags") or "",
                    )
                    result.imported += 1
                except AppError as exc:
                    result.skipped += 1
                    result.errors.append(f"row {row_no}: {exc.message}")

        return result

    def export_csv(
        self,
        output: Path,
        *,
        month: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> int:
        if month:
            month = validate_month(month)
        if not month and not (date_from and date_to):
            raise AppError(
                "export에는 --month 또는 --from과 --to가 필요합니다.",
                "예: export --out export.csv --month 2026-08",
            )
        if month and (date_from or date_to):
            raise AppError("--month와 --from/--to 조건은 한 번에 하나의 방식만 사용하세요.")

        output.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
            writer.writeheader()

            if month:
                source = (
                    transaction
                    for transaction in self.transactions.iter_latest()
                    if transaction.date.startswith(month + "-")
                )
            else:
                source = self.search_transactions(date_from=date_from, date_to=date_to)

            for transaction in source:
                writer.writerow(
                    {
                        "date": transaction.date,
                        "type": transaction.type,
                        "category": transaction.category,
                        "amount": transaction.amount,
                        "memo": transaction.memo,
                        "tags": ",".join(transaction.tags),
                    }
                )
                count += 1

        return count
