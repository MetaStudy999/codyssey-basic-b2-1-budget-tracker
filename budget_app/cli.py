from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .decorators import cli_guard
from .exceptions import BudgetError
from .services import BudgetService


def format_transaction(tx: object) -> str:
    transaction = tx
    tags = ",".join(transaction.tags)
    suffix = f" | tags={tags}" if tags else ""
    return (
        f"{transaction.id} | {transaction.date} | {transaction.type} | "
        f"{transaction.category} | {transaction.amount} | {transaction.memo}{suffix}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m budget_app", description="B2-1 파일 기반 용돈 기입장")
    parser.add_argument("--data-dir", default="data", help="영속 데이터 폴더 (기본: ./data)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("add", help="대화형으로 거래 추가")

    list_parser = subparsers.add_parser("list", help="최신순 거래 목록")
    list_parser.add_argument("--limit", type=int, default=20)

    search = subparsers.add_parser("search", help="조건 검색")
    search.add_argument("--from", dest="date_from")
    search.add_argument("--to", dest="date_to")
    search.add_argument("--category")
    search.add_argument("--type", dest="type_", choices=("income", "expense"))
    search.add_argument("--q", dest="query")
    search.add_argument("--tag")
    search.add_argument("--limit", type=int)

    summary = subparsers.add_parser("summary", help="월별 요약")
    summary.add_argument("--month", required=True)
    summary.add_argument("--top", type=int, default=3)

    update = subparsers.add_parser("update", help="id 기반 거래 수정")
    update.add_argument("--id", required=True)
    update.add_argument("--date")
    update.add_argument("--type", dest="type_", choices=("income", "expense"))
    update.add_argument("--category")
    update.add_argument("--amount")
    update.add_argument("--memo")
    update.add_argument("--tags")

    delete = subparsers.add_parser("delete", help="id 기반 거래 삭제")
    delete.add_argument("--id", required=True)

    category = subparsers.add_parser("category", help="카테고리 관리")
    category_sub = category.add_subparsers(dest="category_command", required=True)
    category_add = category_sub.add_parser("add", help="카테고리 추가")
    category_add.add_argument("--name")
    category_sub.add_parser("list", help="카테고리 목록")
    category_remove = category_sub.add_parser("remove", help="카테고리 삭제")
    category_remove.add_argument("--name", required=True)

    budget = subparsers.add_parser("budget", help="월 예산 관리")
    budget_sub = budget.add_subparsers(dest="budget_command", required=True)
    budget_set = budget_sub.add_parser("set", help="월 예산 저장")
    budget_set.add_argument("--month", required=True)
    budget_set.add_argument("--amount", required=True)

    import_parser = subparsers.add_parser("import", help="CSV 거래 가져오기")
    import_parser.add_argument("--from", dest="import_from", required=True)

    export_parser = subparsers.add_parser("export", help="CSV 거래 내보내기")
    export_parser.add_argument("--out", required=True)
    export_parser.add_argument("--month")
    export_parser.add_argument("--from", dest="date_from")
    export_parser.add_argument("--to", dest="date_to")

    return parser


def _changes(args: argparse.Namespace) -> dict[str, object]:
    changes: dict[str, object] = {}
    for argument, key in (
        ("date", "date"),
        ("type_", "type"),
        ("category", "category"),
        ("amount", "amount"),
        ("memo", "memo"),
        ("tags", "tags"),
    ):
        value = getattr(args, argument, None)
        if value is not None:
            changes[key] = value
    return changes


@cli_guard
def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    service = BudgetService(Path(args.data_dir))

    if args.command == "add":
        tx = service.add_transaction(
            date=input("날짜(YYYY-MM-DD): ").strip(),
            type_=input("타입(income/expense): ").strip(),
            category=input("카테고리: ").strip(),
            amount=input("금액(양수): ").strip(),
            memo=input("메모(선택): ").strip(),
            tags=input("태그(쉼표로 구분, 없으면 엔터): ").strip(),
        )
        print(f"[저장 완료] id={tx.id}")
        return 0

    if args.command == "list":
        rows = list(service.list_transactions(args.limit))
        if not rows:
            print("데이터 없음")
        for tx in rows:
            print(format_transaction(tx))
        return 0

    if args.command == "search":
        if args.limit is not None and args.limit <= 0:
            raise BudgetError("--limit은 1 이상이어야 합니다.", "예: --limit 20")
        found = False
        for tx in service.search_transactions(
            date_from=args.date_from,
            date_to=args.date_to,
            category=args.category,
            type_=args.type_,
            query=args.query,
            tag=args.tag,
            limit=args.limit,
        ):
            found = True
            print(format_transaction(tx))
        if not found:
            print("데이터 없음")
        return 0

    if args.command == "summary":
        result = service.summary(args.month, args.top)
        if result["count"] == 0:
            print("데이터 없음")
        print(f"총 수입: {result['income']}원")
        print(f"총 지출: {result['expense']}원")
        print(f"잔액: {result['balance']}원")
        if result["budget"] is not None:
            print(f"예산: {result['budget']}원 (사용률 {result['usage']:.1f}%)")
            if result["over_budget"]:
                print("[경고] 월 예산을 초과했습니다.")
        print(f"지출 TOP {args.top}")
        for index, (category, total) in enumerate(result["top"], start=1):
            print(f"{index}) {category} {total}원")
        return 0

    if args.command == "update":
        tx = service.update_transaction(args.id, _changes(args))
        print(f"[수정 완료] id={tx.id}")
        return 0

    if args.command == "delete":
        service.delete_transaction(args.id)
        print(f"[삭제 완료] id={args.id}")
        return 0

    if args.command == "category":
        if args.category_command == "list":
            for name in service.categories.list():
                print(f"- {name}")
            return 0
        if args.category_command == "add":
            name = args.name or input("카테고리명: ").strip()
            service.add_category(name)
            print(f"[저장 완료] category={name}")
            return 0
        if args.category_command == "remove":
            service.remove_category(args.name)
            print(f"[삭제 완료] category={args.name}")
            return 0

    if args.command == "budget" and args.budget_command == "set":
        amount = service.set_budget(args.month, args.amount)
        print(f"[저장 완료] {args.month} 예산 {amount}원")
        return 0

    if args.command == "import":
        count = service.import_csv(Path(args.import_from))
        print(f"[완료] imported={count}, skipped=0")
        return 0

    if args.command == "export":
        count = service.export_csv(
            Path(args.out),
            month=args.month,
            date_from=args.date_from,
            date_to=args.date_to,
        )
        print(f"[완료] {args.out} ({count} records)")
        return 0

    raise BudgetError("알 수 없는 명령입니다.", "--help로 사용법을 확인해 주세요.")
