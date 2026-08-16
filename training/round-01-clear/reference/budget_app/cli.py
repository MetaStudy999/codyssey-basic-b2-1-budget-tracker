from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .errors import AppError
from .models import Transaction
from .services import BudgetService
from .utils import handle_cli_errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m budget_app",
        description="파일 기반 용돈 기입장 (Codyssey B2-1 Reference)",
    )
    parser.add_argument("--data-dir", default="./data", help="저장 폴더 (기본: ./data)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("add", help="대화형으로 거래 추가")

    list_parser = sub.add_parser("list", help="최신순 거래 목록")
    list_parser.add_argument("--limit", type=int, default=20, help="출력 건수 (기본: 20)")

    search = sub.add_parser("search", help="조건 기반 거래 검색")
    search.add_argument("--from", dest="date_from")
    search.add_argument("--to", dest="date_to")
    search.add_argument("--category")
    search.add_argument("--type", choices=("income", "expense"))
    search.add_argument("--q", help="메모 키워드")
    search.add_argument("--tag")

    summary = sub.add_parser("summary", help="월별 요약")
    summary.add_argument("--month", required=True, help="YYYY-MM")
    summary.add_argument("--top", type=int, default=3, help="지출 카테고리 TOP N")

    update = sub.add_parser("update", help="ID 기반 거래 수정 (옵션 방식)")
    update.add_argument("--id", required=True, dest="transaction_id")
    update.add_argument("--date")
    update.add_argument("--type", choices=("income", "expense"))
    update.add_argument("--category")
    update.add_argument("--amount", type=int)
    update.add_argument("--memo")
    update.add_argument("--tags", help="쉼표 구분 태그. 빈 문자열이면 모두 제거")

    delete = sub.add_parser("delete", help="ID 기반 거래 삭제")
    delete.add_argument("--id", required=True, dest="transaction_id")

    budget = sub.add_parser("budget", help="월 예산 관리")
    budget_sub = budget.add_subparsers(dest="budget_command", required=True)
    budget_set = budget_sub.add_parser("set", help="월 예산 저장")
    budget_set.add_argument("--month", required=True)
    budget_set.add_argument("--amount", type=int, required=True)

    category = sub.add_parser("category", help="카테고리 관리")
    category_sub = category.add_subparsers(dest="category_command", required=True)
    category_add = category_sub.add_parser("add", help="카테고리 추가")
    category_add.add_argument("--name")
    category_sub.add_parser("list", help="카테고리 목록")
    category_remove = category_sub.add_parser("remove", help="카테고리 삭제")
    category_remove.add_argument("--name", required=True)

    import_parser = sub.add_parser("import", help="CSV 거래 가져오기")
    import_parser.add_argument("--from", dest="source", required=True)

    export = sub.add_parser("export", help="CSV 거래 내보내기")
    export.add_argument("--out", required=True)
    export.add_argument("--month")
    export.add_argument("--from", dest="date_from")
    export.add_argument("--to", dest="date_to")

    return parser


def format_transaction(transaction: Transaction) -> str:
    tags = ",".join(transaction.tags)
    memo_and_tags = transaction.memo
    if tags:
        memo_and_tags += f" [{tags}]" if memo_and_tags else f"[{tags}]"
    return (
        f"{transaction.id} | {transaction.date} | {transaction.type:<7} | "
        f"{transaction.category:<12} | {transaction.amount:>10} | {memo_and_tags}"
    )


def prompt_add(service: BudgetService) -> Transaction:
    print("등록된 카테고리: " + ", ".join(service.list_categories()))
    date = input("날짜(YYYY-MM-DD): ").strip()
    type_value = input("타입(income/expense): ").strip()
    category = input("카테고리: ").strip()
    amount = input("금액(양수): ").strip()
    memo = input("메모(선택): ").strip()
    tags = input("태그(쉼표로 구분, 없으면 엔터): ").strip()
    return service.add_transaction(
        date=date,
        type=type_value,
        category=category,
        amount=amount,
        memo=memo,
        tags=tags,
    )


@handle_cli_errors
def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    service = BudgetService(Path(args.data_dir))

    if args.command == "add":
        transaction = prompt_add(service)
        print(f"[저장 완료] id={transaction.id}")
        return 0

    if args.command == "list":
        count = 0
        for transaction in service.list_transactions(args.limit):
            print(format_transaction(transaction))
            count += 1
        if count == 0:
            print("[안내] 거래 데이터가 없습니다.")
        return 0

    if args.command == "search":
        count = 0
        for transaction in service.search_transactions(
            date_from=args.date_from,
            date_to=args.date_to,
            category=args.category,
            type=args.type,
            query=args.q,
            tag=args.tag,
        ):
            print(format_transaction(transaction))
            count += 1
        if count == 0:
            print("[안내] 조건에 맞는 거래가 없습니다.")
        return 0

    if args.command == "summary":
        result = service.summary(args.month, args.top)
        if result["count"] == 0:
            print(f"[안내] {result['month']} 데이터 없음")
            return 0
        print(f"총 수입: {result['income']}원")
        print(f"총 지출: {result['expense']}원")
        print(f"잔액: {result['balance']}원")
        if result["budget"] is not None:
            print(f"예산: {result['budget']}원 (사용률 {result['budget_usage']:.1f}%)")
            if result["over_budget"]:
                print("[WARNING] 월 예산을 초과했습니다.")
        print(f"지출 TOP {args.top}")
        for index, (category, amount) in enumerate(result["top"], start=1):
            print(f"{index}) {category} {amount}원")
        return 0

    if args.command == "update":
        transaction = service.update_transaction(
            args.transaction_id,
            date=args.date,
            type=args.type,
            category=args.category,
            amount=args.amount,
            memo=args.memo,
            tags=args.tags,
        )
        print(f"[수정 완료] id={transaction.id}")
        return 0

    if args.command == "delete":
        service.delete_transaction(args.transaction_id)
        print(f"[삭제 완료] id={args.transaction_id}")
        return 0

    if args.command == "budget" and args.budget_command == "set":
        budget = service.set_budget(args.month, args.amount)
        print(f"[저장 완료] {budget.month} 예산 {budget.amount}원")
        return 0

    if args.command == "category":
        if args.category_command == "list":
            for name in service.list_categories():
                print(f"- {name}")
            return 0
        if args.category_command == "add":
            name = (args.name or input("카테고리명: ")).strip()
            if service.add_category(name):
                print(f"[저장 완료] category={name}")
            else:
                print(f"[안내] 이미 존재하는 카테고리입니다: {name}")
            return 0
        if args.category_command == "remove":
            service.remove_category(args.name)
            print(f"[삭제 완료] category={args.name}")
            return 0

    if args.command == "import":
        result = service.import_csv(Path(args.source))
        print(f"[완료] imported={result.imported}, skipped={result.skipped}")
        for error in result.errors:
            print(f"[SKIP] {error}")
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

    raise AppError("알 수 없는 명령입니다.", "--help로 사용 가능한 명령을 확인하세요.")
