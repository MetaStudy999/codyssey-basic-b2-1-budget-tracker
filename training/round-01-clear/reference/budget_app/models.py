from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Transaction:
    """One income/expense record stored in transactions.jsonl."""

    id: str
    type: str
    date: str
    amount: int
    category: str
    memo: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Transaction":
        tags = raw.get("tags", [])
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        return cls(
            id=str(raw["id"]),
            type=str(raw["type"]),
            date=str(raw["date"]),
            amount=int(raw["amount"]),
            category=str(raw["category"]),
            memo=str(raw.get("memo", "")),
            tags=list(tags),
        )


@dataclass(slots=True)
class Budget:
    month: str
    amount: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ImportResult:
    imported: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
