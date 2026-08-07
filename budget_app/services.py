from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Iterator

from .exceptions import BudgetError
from .models import Transaction, parse_tags, validate_amount, validate_date, validate_month
from .storage import BudgetStore, CategoryStore, DataPaths, TransactionRepository

CSV_FIELDS = ("date", "type", "category", "amount", "memo", "tags")


class BudgetService:
    def __init__(self, data_dir: Path) -> None:
        self.paths = DataPaths(data_dir)
        self.paths.initialize()
        self.transactions = TransactionRepository(self.paths)
        self.categories = CategoryStore(self.paths)
        self.budgets = BudgetStore(self.paths)

    def _require_category(self, category: str) -> None:
        if category not in self.categories.list():
            raise BudgetError(
                f"등록되지 않은 카테고리입니다: {category}",
                "category list로 확인하거나 category add로 먼저 등록해 주세요.",
            )

    def add_transaction(
        self,
        *,
        date: str,
        type_: str,
        category: str,
        amount: int | str,
        memo: str = "",
        tags: str | None = None,
    ) -> Transaction:
        self._require_category(category)
        tx = Transaction(
            id=self.transactions.next_id(),
            type=type_,
            date=date,
            amount=validate_amount(amount),
            category=category,
            memo=memo,
            tags=parse_tags(tags),
        )
        self.transactions.add(tx)
        return tx

    def list_transactions(self, limit: int) -> Iterator[Transaction]:
        if limit <= 0:
            raise BudgetError("--limit은 1 이상이어야 합니다.", "예: --limit 20")
        for index, tx in enumerate(self.transactions.iter_transactions()):
            if index >= limit:
                break
            yield tx

    def search_transactions(
        self,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        category: str | None = None,
        type_: str | None = None,
        query: str | None = None,
        tag: str | None = None,
        limit: int | None = None,
    ) -> Iterator[Transaction]:
        if date_from:
            validate_date(date_from)
        if date_to:
            validate_date(date_to)
        if date_from and date_to and date_from > date_to:
            raise BudgetError("검색 시작일이 종료일보다 늦습니다.", "--from과 --to 값을 다시 확인해 주세요.")
        emitted = 0
        for tx in self.transactions.iter_transactions():
            if date_from and tx.date < date_from:
                continue
            if date_to and tx.date > date_to:
                continue
            if category and tx.category != category:
                continue
            if type_ and tx.type != type_:
                continue
            if query and query.lower() not in tx.memo.lower():
                continue
            if tag and tag not in tx.tags:
                continue
            yield tx
            emitted += 1
            if limit is not None and emitted >= limit:
                return

    def update_transaction(self, transaction_id: str, changes: dict[str, object]) -> Transaction:
        if not changes:
            raise BudgetError("수정할 값이 없습니다.", "--date/--type/--category/--amount/--memo/--tags 중 하나를 지정해 주세요.")
        if "category" in changes:
            self._require_category(str(changes["category"]))
        if "date" in changes:
            validate_date(str(changes["date"]))
        if "amount" in changes:
            changes["amount"] = validate_amount(changes["amount"])
        if "tags" in changes:
            changes["tags"] = parse_tags(str(changes["tags"]))
        return self.transactions.update(transaction_id, changes)

    def delete_transaction(self, transaction_id: str) -> None:
        self.transactions.delete(transaction_id)

    def add_category(self, name: str) -> None:
        self.categories.add(name)

    def remove_category(self, name: str) -> None:
        for tx in self.transactions.iter_transactions():
            if tx.category == name:
                raise BudgetError(
                    f"사용 중인 카테고리는 삭제할 수 없습니다: {name}",
                    "해당 거래의 카테고리를 먼저 update한 뒤 다시 삭제해 주세요.",
                )
        self.categories.remove(name)

    def set_budget(self, month: str, amount: int | str) -> int:
        month = validate_month(month)
        normalized = validate_amount(amount)
        self.budgets.set(month, normalized)
        return normalized

    def summary(self, month: str, top: int) -> dict[str, object]:
        validate_month(month)
        if top <= 0:
            raise BudgetError("--top은 1 이상이어야 합니다.", "예: --top 3")
        income = 0
        expense = 0
        category_totals: dict[str, int] = defaultdict(int)
        count = 0
        for tx in self.transactions.iter_transactions():
            if not tx.date.startswith(month + "-"):
                continue
            count += 1
            if tx.type == "income":
                income += tx.amount
            else:
                expense += tx.amount
                category_totals[tx.category] += tx.amount
        ranked = sorted(category_totals.items(), key=lambda item: (-item[1], item[0]))[:top]
        budget = self.budgets.get(month)
        usage = (expense / budget * 100.0) if budget else None
        return {
            "count": count,
            "income": income,
            "expense": expense,
            "balance": income - expense,
            "top": ranked,
            "budget": budget,
            "usage": usage,
            "over_budget": bool(budget is not None and expense > budget),
        }

    def export_csv(
        self,
        output: Path,
        *,
        month: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> int:
        if not month and not (date_from and date_to):
            raise BudgetError(
                "export에는 --month 또는 --from/--to 범위가 필요합니다.",
                "예: export --out out.csv --month 2026-08",
            )
        if month:
            validate_month(month)
        if date_from:
            validate_date(date_from)
        if date_to:
            validate_date(date_to)
        if date_from and date_to and date_from > date_to:
            raise BudgetError("내보내기 시작일이 종료일보다 늦습니다.", "--from과 --to 값을 다시 확인해 주세요.")
        output.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        try:
            with output.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
                writer.writeheader()
                for tx in self.transactions.iter_transactions():
                    if month and not tx.date.startswith(month + "-"):
                        continue
                    if date_from and tx.date < date_from:
                        continue
                    if date_to and tx.date > date_to:
                        continue
                    writer.writerow(
                        {
                            "date": tx.date,
                            "type": tx.type,
                            "category": tx.category,
                            "amount": tx.amount,
                            "memo": tx.memo,
                            "tags": ",".join(tx.tags),
                        }
                    )
                    count += 1
        except OSError as exc:
            raise BudgetError("CSV 파일을 저장할 수 없습니다.", str(exc)) from exc
        return count

    def import_csv(self, source: Path) -> int:
        """Validate every row first; commit all rows atomically only if the file is fully valid."""
        pending: list[Transaction] = []
        categories = set(self.categories.list())
        try:
            with source.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                if reader.fieldnames is None:
                    raise BudgetError("CSV 헤더가 없습니다.", f"필수 헤더: {', '.join(CSV_FIELDS)}")
                normalized_headers = tuple(reader.fieldnames)
                missing = [field for field in CSV_FIELDS if field not in normalized_headers]
                if missing:
                    raise BudgetError("CSV 필수 컬럼이 없습니다: " + ", ".join(missing), f"필수 헤더: {', '.join(CSV_FIELDS)}")
                next_number = int(self.transactions.next_id()[3:])
                for row_no, row in enumerate(reader, start=2):
                    try:
                        category = (row.get("category") or "").strip()
                        if category not in categories:
                            raise BudgetError(
                                f"등록되지 않은 카테고리입니다: {category}",
                                "category add로 먼저 등록하거나 CSV 값을 수정해 주세요.",
                            )
                        tx = Transaction(
                            id=f"TX-{next_number:06d}",
                            type=(row.get("type") or "").strip(),
                            date=(row.get("date") or "").strip(),
                            amount=validate_amount((row.get("amount") or "").strip()),
                            category=category,
                            memo=row.get("memo") or "",
                            tags=parse_tags(row.get("tags")),
                        )
                    except BudgetError as exc:
                        raise BudgetError(
                            f"CSV {row_no}번째 행이 올바르지 않습니다: {exc}",
                            exc.hint + " 전체 import는 취소되었으며 기존 데이터는 변경되지 않았습니다.",
                        ) from exc
                    pending.append(tx)
                    next_number += 1
        except FileNotFoundError as exc:
            raise BudgetError(f"CSV 파일을 찾을 수 없습니다: {source}", "--from 경로를 확인해 주세요.") from exc
        except UnicodeError as exc:
            raise BudgetError("CSV 파일을 UTF-8로 읽을 수 없습니다.", "UTF-8 인코딩으로 저장한 뒤 다시 시도해 주세요.") from exc
        except OSError as exc:
            raise BudgetError("CSV 파일을 열 수 없습니다.", str(exc)) from exc
        if pending:
            self.transactions.add_many(pending)
        return len(pending)
