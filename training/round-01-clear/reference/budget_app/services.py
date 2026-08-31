"""가계부의 업무 규칙(Business Logic)을 담당하는 Service 계층입니다.

Service는 CLI와 Repository 사이에서 '무엇이 올바른 거래인가?', '어떻게 검색하고
요약할 것인가?' 같은 규칙을 처리합니다. 파일을 직접 읽고 쓰는 세부 구현은
Repository에 맡기고, CLI는 사용자 입력/출력에 집중하게 합니다.

흐름을 단순화하면 다음과 같습니다.

사용자 입력 -> CLI -> BudgetService -> Repository -> JSONL 파일
                           |
                           +-> 검증/검색/집계/예산/카테고리 규칙
"""

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

# 첫 실행 시 자동으로 만들어 주는 기본 카테고리입니다.
DEFAULT_CATEGORIES = ("food", "transport", "rent", "salary", "etc")

# 외부 CSV와 데이터를 주고받을 때 사용하는 고정 컬럼 순서입니다.
CSV_COLUMNS = ("date", "type", "category", "amount", "memo", "tags")


class BudgetService:
    """거래·카테고리·예산·CSV 기능의 업무 규칙을 한곳에서 관리합니다."""

    def __init__(self, data_dir: Path) -> None:
        """같은 data_dir을 사용하는 세 Repository를 준비합니다."""

        self.data_dir = data_dir
        self.transactions = TransactionRepository(data_dir)
        self.categories = CategoryRepository(data_dir)
        self.budgets = BudgetRepository(data_dir)

        # 첫 실행에서 category 파일이 비어 있다면 기본 카테고리를 채웁니다.
        self._initialize_categories()

    def _initialize_categories(self) -> None:
        """카테고리가 하나도 없을 때만 기본 카테고리를 추가합니다."""

        if self.categories.list():
            # 이미 사용자가 만든 카테고리가 있다면 덮어쓰지 않습니다.
            return

        for name in DEFAULT_CATEGORIES:
            self.categories.add(name)

    def _require_category(self, name: str) -> str:
        """카테고리가 등록되어 있는지 확인하고 정규화된 이름을 반환합니다."""

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
        """입력값을 검증한 뒤 새 거래를 만들어 저장합니다.

        ``*`` 뒤의 인수는 이름을 명시해서 전달해야 합니다. 예를 들어
        ``add_transaction(date="2026-08-31", ...)``처럼 사용하므로 각 값의 의미를
        헷갈리기 어렵습니다.
        """

        transaction = Transaction(
            # 현재 저장된 거래를 기준으로 새 고유 ID를 만듭니다.
            id=self.transactions.next_id(),
            # 아래 검증 함수들은 잘못된 값이면 AppError를 발생시킵니다.
            type=validate_type(type),
            date=validate_date(date),
            amount=positive_int(amount),
            category=self._require_category(category),
            memo=memo.strip(),
            tags=parse_tags(tags),
        )

        # 모든 검증을 통과한 거래만 실제 파일에 기록합니다.
        self.transactions.append(transaction)
        return transaction

    def list_transactions(self, limit: int = 20) -> Generator[Transaction, None, None]:
        """최신 거래부터 최대 ``limit``건을 제너레이터로 반환합니다."""

        if limit <= 0:
            raise AppError("--limit은 1 이상이어야 합니다.")

        count = 0
        for transaction in self.transactions.iter_latest():
            # yield를 사용하므로 전체 결과를 한꺼번에 list로 만들지 않습니다.
            yield transaction
            count += 1

            # 필요한 개수만 읽었으면 더 이상 파일을 읽지 않고 즉시 끝냅니다.
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
        """여러 검색 조건을 조합해 맞는 거래만 최신순으로 yield합니다."""

        # 전달된 조건만 검증합니다. None은 '그 조건을 사용하지 않음'이라는 뜻입니다.
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

        # 메모 검색은 대소문자의 영향을 줄이기 위해 소문자로 비교합니다.
        normalized_query = query.lower() if query else None
        normalized_tag = tag.strip() if tag else None

        # 최신순 스트림에서 조건에 맞지 않는 거래는 continue로 건너뜁니다.
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

            # 여기까지 왔다는 것은 모든 지정 조건을 통과했다는 뜻입니다.
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
        """ID로 거래를 찾아 지정된 필드만 수정합니다.

        값이 ``None``인 필드는 기존 값을 유지합니다. 따라서 사용자는 바꾸고 싶은
        필드만 옵션으로 전달할 수 있습니다.
        """

        if all(value is None for value in (date, type, category, amount, memo, tags)):
            raise AppError("수정할 필드를 하나 이상 지정해야 합니다.")

        def transform(current: Transaction) -> Transaction:
            """기존 객체에서 필요한 필드만 바꾼 새 Transaction을 만듭니다."""

            # dataclasses.replace()는 원본 dataclass를 직접 수정하지 않고
            # 필드 일부만 바꾼 새로운 객체를 만들어 줍니다.
            return replace(
                current,
                date=validate_date(date) if date is not None else current.date,
                type=validate_type(type) if type is not None else current.type,
                category=self._require_category(category) if category is not None else current.category,
                amount=positive_int(amount) if amount is not None else current.amount,
                memo=memo.strip() if memo is not None else current.memo,
                tags=parse_tags(tags) if tags is not None else current.tags,
            )

        # Repository는 ID를 찾아 transform을 적용하고 파일을 원자적으로 재작성합니다.
        return self.transactions.update(transaction_id, transform)

    def delete_transaction(self, transaction_id: str) -> None:
        """ID에 해당하는 거래를 삭제하고, 없으면 친절한 오류를 발생시킵니다."""

        if not self.transactions.delete(transaction_id):
            raise AppError("삭제할 거래를 찾을 수 없습니다.", f"id={transaction_id}가 맞는지 list로 확인하세요.")

    def summary(self, month: str, top: int = 3) -> dict[str, Any]:
        """한 달의 수입·지출·잔액·카테고리 순위·예산 사용률을 계산합니다."""

        month = validate_month(month)
        if top <= 0:
            raise AppError("--top은 1 이상이어야 합니다.")

        income = 0
        expense = 0

        # defaultdict(int)는 처음 보는 category도 자동으로 0부터 더할 수 있게 합니다.
        expense_by_category: dict[str, int] = defaultdict(int)
        count = 0

        for transaction in self.transactions.iter_all():
            # 날짜 문자열이 '2026-08-'로 시작하면 2026년 8월 거래입니다.
            if not transaction.date.startswith(month + "-"):
                continue

            count += 1
            if transaction.type == "income":
                income += transaction.amount
            else:
                expense += transaction.amount
                expense_by_category[transaction.category] += transaction.amount

        # 금액이 큰 순(-item[1])으로 정렬하고, 금액이 같으면 category 이름 순으로 정렬합니다.
        ranking = sorted(expense_by_category.items(), key=lambda item: (-item[1], item[0]))[:top]

        # 같은 월에 저장된 예산이 있으면 사용률을 계산합니다.
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
        """월과 금액을 검증한 뒤 예산을 저장합니다."""

        budget = Budget(month=validate_month(month), amount=positive_int(amount, "예산"))
        self.budgets.set(budget)
        return budget

    def list_categories(self) -> list[str]:
        """현재 등록된 카테고리를 모두 반환합니다."""

        return self.categories.list()

    def add_category(self, name: str) -> bool:
        """새 카테고리를 추가합니다. 이미 존재하면 False를 반환합니다."""

        return self.categories.add(name)

    def remove_category(self, name: str) -> None:
        """사용 중이 아닌 카테고리만 삭제합니다.

        거래가 참조하는 카테고리를 먼저 삭제하면 기존 거래가 유효하지 않은 상태가
        되므로, 사용 중인지 전체 거래를 확인한 뒤 삭제합니다.
        """

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
        """CSV 거래를 읽어 정상 행은 저장하고 잘못된 행은 건너뜁니다.

        이 Reference는 Partial Success(부분 성공) 정책을 사용합니다. 즉 파일 전체를
        한 번에 실패시키지 않고, 각 행을 독립적으로 검증하여 정상 행은 import하고
        잘못된 행은 ``skipped``와 오류 이유에 기록합니다.
        """

        if not source.exists():
            raise AppError(f"가져올 CSV 파일이 없습니다: {source}")

        result = ImportResult()

        # utf-8-sig는 일반 UTF-8뿐 아니라 BOM이 붙은 UTF-8 CSV도 읽을 수 있습니다.
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)

            if reader.fieldnames is None:
                raise AppError("CSV 헤더가 없습니다.")

            # 공식 스키마의 필수 컬럼이 빠졌는지 먼저 확인합니다.
            missing = [name for name in CSV_COLUMNS if name not in reader.fieldnames]
            if missing:
                raise AppError("CSV 필수 컬럼이 없습니다: " + ", ".join(missing))

            # 헤더가 1행이므로 실제 데이터의 첫 행 번호는 2부터 시작합니다.
            for row_no, row in enumerate(reader, start=2):
                try:
                    # 기존 add_transaction()을 재사용하므로 CSV도 CLI 입력과 같은
                    # 날짜/type/금액/category 검증 규칙을 적용받습니다.
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
                    # 한 행의 오류가 나머지 정상 행까지 막지 않게 건너뛰고 이유를 기록합니다.
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
        """월 또는 날짜 범위에 맞는 거래를 공식 CSV 스키마로 내보냅니다."""

        if month:
            month = validate_month(month)

        # Reference는 '--month' 방식 또는 '--from + --to' 방식 중 하나를 요구합니다.
        if not month and not (date_from and date_to):
            raise AppError(
                "export에는 --month 또는 --from과 --to가 필요합니다.",
                "예: export --out export.csv --month 2026-08",
            )

        # 서로 다른 두 필터 방식이 동시에 들어오면 의미가 모호해지므로 막습니다.
        if month and (date_from or date_to):
            raise AppError("--month와 --from/--to 조건은 한 번에 하나의 방식만 사용하세요.")

        # 출력 파일의 상위 폴더가 없으면 먼저 만들어 줍니다.
        output.parent.mkdir(parents=True, exist_ok=True)
        count = 0

        with output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
            writer.writeheader()

            if month:
                # generator expression을 사용해 해당 월의 거래만 한 건씩 통과시킵니다.
                source = (
                    transaction
                    for transaction in self.transactions.iter_latest()
                    if transaction.date.startswith(month + "-")
                )
            else:
                # 날짜 범위 export는 기존 search 로직을 재사용합니다.
                source = self.search_transactions(date_from=date_from, date_to=date_to)

            for transaction in source:
                writer.writerow(
                    {
                        "date": transaction.date,
                        "type": transaction.type,
                        "category": transaction.category,
                        "amount": transaction.amount,
                        "memo": transaction.memo,
                        # 내부에서는 list인 tags를 CSV 한 칸에 넣기 위해 쉼표 문자열로 바꿉니다.
                        "tags": ",".join(transaction.tags),
                    }
                )
                count += 1

        # CLI가 '(N records)'처럼 표시할 수 있도록 실제 출력 건수를 반환합니다.
        return count
