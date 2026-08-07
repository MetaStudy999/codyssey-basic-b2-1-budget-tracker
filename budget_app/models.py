from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping

from .exceptions import BudgetError

VALID_TYPES = {"income", "expense"}


def validate_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise BudgetError(
            f"날짜 형식이 올바르지 않습니다: {value}",
            "YYYY-MM-DD 형식으로 입력해 주세요. 예: 2026-08-08",
        ) from exc
    return value


def validate_month(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise BudgetError(
            f"월 형식이 올바르지 않습니다: {value}",
            "YYYY-MM 형식으로 입력해 주세요. 예: 2026-08",
        ) from exc
    return value


def validate_amount(value: int | str) -> int:
    try:
        amount = int(value)
    except (TypeError, ValueError) as exc:
        raise BudgetError("금액은 정수여야 합니다.", "1 이상의 정수를 입력해 주세요.") from exc
    if amount <= 0:
        raise BudgetError("금액은 0보다 커야 합니다.", "1 이상의 정수를 입력해 주세요.")
    return amount


def parse_tags(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(slots=True)
class Transaction:
    id: str
    type: str
    date: str
    amount: int
    category: str
    memo: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        validate_date(self.date)
        self.amount = validate_amount(self.amount)
        if self.type not in VALID_TYPES:
            raise BudgetError(
                f"허용되지 않은 거래 타입입니다: {self.type}",
                "income 또는 expense 중 하나를 사용해 주세요.",
            )
        self.category = self.category.strip()
        if not self.category:
            raise BudgetError("카테고리는 비어 있을 수 없습니다.", "등록된 카테고리명을 입력해 주세요.")
        self.memo = self.memo.strip()
        self.tags = [tag.strip() for tag in self.tags if tag.strip()]

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "Transaction":
        raw_tags = data.get("tags", [])
        if isinstance(raw_tags, str):
            tags = parse_tags(raw_tags)
        else:
            tags = [str(tag) for tag in raw_tags] if isinstance(raw_tags, list) else []
        return cls(
            id=str(data["id"]),
            type=str(data["type"]),
            date=str(data["date"]),
            amount=validate_amount(data["amount"]),
            category=str(data["category"]),
            memo=str(data.get("memo", "")),
            tags=tags,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "type": self.type,
            "date": self.date,
            "amount": self.amount,
            "category": self.category,
            "memo": self.memo,
            "tags": self.tags,
        }
