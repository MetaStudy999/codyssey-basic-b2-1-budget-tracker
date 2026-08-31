"""터미널 명령을 해석하고 사용자에게 결과를 보여 주는 CLI 계층입니다.

CLI(Command Line Interface, 명령줄 인터페이스)는 사용자가 입력한 명령을 읽고
``BudgetService``의 적절한 기능을 호출한 뒤 결과를 화면에 출력합니다.

예를 들어 다음 명령은

``python -m budget_app --data-dir /tmp/data list --limit 10``

1. argparse가 ``list`` 명령과 ``--limit 10``을 해석하고,
2. ``BudgetService.list_transactions(10)``을 호출하고,
3. 반환된 거래를 사람이 읽기 좋은 한 줄 형식으로 출력합니다.

중요한 설계 원칙은 CLI가 JSONL 파일을 직접 수정하지 않는다는 것입니다.
저장과 업무 규칙은 Repository/Service에 맡기고, 이 파일은 입력/출력에 집중합니다.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .errors import AppError
from .models import Transaction
from .services import BudgetService
from .utils import handle_cli_errors


def build_parser() -> argparse.ArgumentParser:
    """B2-1에서 사용할 모든 명령과 옵션을 argparse에 등록합니다.

    argparse는 사용자의 터미널 문자열을 Python 객체 ``args``로 바꿔 줍니다.
    또한 ``--help`` 화면, 필수 옵션 검사, choices 검사도 자동으로 처리합니다.
    """

    # 가장 바깥쪽 parser는 ``python -m budget_app`` 자체를 설명합니다.
    parser = argparse.ArgumentParser(
        prog="python -m budget_app",
        description="파일 기반 용돈 기입장 (Codyssey B2-1 Reference)",
    )

    # --data-dir은 모든 command가 공통으로 사용하는 전역 옵션입니다.
    # 실습에서는 /tmp 같은 별도 폴더를 주어 개인 데이터와 검증 데이터를 분리할 수 있습니다.
    parser.add_argument("--data-dir", default="./data", help="저장 폴더 (기본: ./data)")

    # subparser는 add/list/search처럼 '하위 명령'을 만들 때 사용합니다.
    # dest="command"이므로 선택한 명령 이름이 args.command에 저장됩니다.
    sub = parser.add_subparsers(dest="command", required=True)

    # ------------------------------------------------------------------
    # add: 옵션 대신 실행 후 input()으로 값을 받는 대화형 명령
    # ------------------------------------------------------------------
    sub.add_parser("add", help="대화형으로 거래 추가")

    # ------------------------------------------------------------------
    # list: 최신 거래 목록
    # ------------------------------------------------------------------
    list_parser = sub.add_parser("list", help="최신순 거래 목록")
    list_parser.add_argument("--limit", type=int, default=20, help="출력 건수 (기본: 20)")

    # ------------------------------------------------------------------
    # search: 여러 조건을 선택적으로 조합하는 검색 명령
    # ------------------------------------------------------------------
    search = sub.add_parser("search", help="조건 기반 거래 검색")

    # Python 예약어/관례와 구분하기 위해 --from은 args.date_from으로 저장합니다.
    search.add_argument("--from", dest="date_from")
    search.add_argument("--to", dest="date_to")
    search.add_argument("--category")

    # choices를 주면 argparse가 income/expense 이외의 입력을 즉시 거부합니다.
    search.add_argument("--type", choices=("income", "expense"))
    search.add_argument("--q", help="메모 키워드")
    search.add_argument("--tag")

    # ------------------------------------------------------------------
    # summary: 월별 수입/지출/잔액/예산/카테고리 순위
    # ------------------------------------------------------------------
    summary = sub.add_parser("summary", help="월별 요약")
    summary.add_argument("--month", required=True, help="YYYY-MM")
    summary.add_argument("--top", type=int, default=3, help="지출 카테고리 TOP N")

    # ------------------------------------------------------------------
    # update: ID는 필수이고 변경할 필드는 선택적으로 전달
    # ------------------------------------------------------------------
    update = sub.add_parser("update", help="ID 기반 거래 수정 (옵션 방식)")
    update.add_argument("--id", required=True, dest="transaction_id")
    update.add_argument("--date")
    update.add_argument("--type", choices=("income", "expense"))
    update.add_argument("--category")
    update.add_argument("--amount", type=int)
    update.add_argument("--memo")
    update.add_argument("--tags", help="쉼표 구분 태그. 빈 문자열이면 모두 제거")

    # ------------------------------------------------------------------
    # delete: ID 한 건 삭제
    # ------------------------------------------------------------------
    delete = sub.add_parser("delete", help="ID 기반 거래 삭제")
    delete.add_argument("--id", required=True, dest="transaction_id")

    # ------------------------------------------------------------------
    # budget set: budget 안에 다시 set 하위 명령을 둡니다.
    # 예) python -m budget_app budget set --month 2026-08 --amount 100000
    # ------------------------------------------------------------------
    budget = sub.add_parser("budget", help="월 예산 관리")
    budget_sub = budget.add_subparsers(dest="budget_command", required=True)
    budget_set = budget_sub.add_parser("set", help="월 예산 저장")
    budget_set.add_argument("--month", required=True)
    budget_set.add_argument("--amount", type=int, required=True)

    # ------------------------------------------------------------------
    # category add/list/remove
    # ------------------------------------------------------------------
    category = sub.add_parser("category", help="카테고리 관리")
    category_sub = category.add_subparsers(dest="category_command", required=True)

    category_add = category_sub.add_parser("add", help="카테고리 추가")
    # --name을 생략하면 main()에서 input()으로 물어볼 수 있도록 required=True를 쓰지 않습니다.
    category_add.add_argument("--name")

    category_sub.add_parser("list", help="카테고리 목록")

    category_remove = category_sub.add_parser("remove", help="카테고리 삭제")
    category_remove.add_argument("--name", required=True)

    # ------------------------------------------------------------------
    # import/export: 외부 CSV와 내부 JSONL 사이의 데이터 교환
    # ------------------------------------------------------------------
    import_parser = sub.add_parser("import", help="CSV 거래 가져오기")
    # --from은 Python에서 의미가 분명한 source라는 속성 이름으로 저장합니다.
    import_parser.add_argument("--from", dest="source", required=True)

    export = sub.add_parser("export", help="CSV 거래 내보내기")
    export.add_argument("--out", required=True)
    export.add_argument("--month")
    export.add_argument("--from", dest="date_from")
    export.add_argument("--to", dest="date_to")

    return parser


def format_transaction(transaction: Transaction) -> str:
    """Transaction 한 건을 터미널에서 읽기 좋은 한 줄 문자열로 바꿉니다."""

    # 내부 tags는 list[str]이므로 화면에는 쉼표로 연결해서 보여 줍니다.
    tags = ",".join(transaction.tags)

    # 메모가 있으면 먼저 넣고, 태그가 있으면 뒤에 [tag1,tag2] 형태로 붙입니다.
    memo_and_tags = transaction.memo
    if tags:
        memo_and_tags += f" [{tags}]" if memo_and_tags else f"[{tags}]"

    # :<7은 왼쪽 정렬, :>10은 오른쪽 정렬입니다.
    # 숫자/텍스트 열을 맞춰 여러 거래를 볼 때 가독성을 높입니다.
    return (
        f"{transaction.id} | {transaction.date} | {transaction.type:<7} | "
        f"{transaction.category:<12} | {transaction.amount:>10} | {memo_and_tags}"
    )


def prompt_add(service: BudgetService) -> Transaction:
    """add 명령에서 사용자에게 거래 필드를 한 항목씩 입력받습니다."""

    # 사용자가 오타로 없는 카테고리를 입력하지 않도록 먼저 등록 목록을 보여 줍니다.
    print("등록된 카테고리: " + ", ".join(service.list_categories()))

    # input()은 항상 문자열을 반환합니다. strip()으로 앞뒤 공백을 제거합니다.
    date = input("날짜(YYYY-MM-DD): ").strip()
    type_value = input("타입(income/expense): ").strip()
    category = input("카테고리: ").strip()
    amount = input("금액(양수): ").strip()
    memo = input("메모(선택): ").strip()
    tags = input("태그(쉼표로 구분, 없으면 엔터): ").strip()

    # 실제 검증과 저장은 CLI가 직접 하지 않고 Service에 맡깁니다.
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
    """CLI의 전체 실행 흐름을 제어하고 성공/실패 종료 코드를 반환합니다.

    ``argv``가 None이면 실제 터미널 인수를 argparse가 읽습니다. 테스트에서는
    ``main(["--data-dir", ...])``처럼 리스트를 직접 전달해 CLI를 검증할 수 있습니다.

    이 함수 위의 ``@handle_cli_errors``가 AppError 등을 잡아 사용자에게 친절하게
    출력하고 오류 종료 코드 2로 바꿉니다.
    """

    # 1) 사용 가능한 명령/옵션 정의를 만듭니다.
    parser = build_parser()

    # 2) 터미널 입력을 파싱하여 args 객체에 저장합니다.
    args = parser.parse_args(argv)

    # 3) 사용자가 지정한 데이터 폴더를 기준으로 Service를 준비합니다.
    service = BudgetService(Path(args.data_dir))

    # ------------------------------------------------------------------
    # ADD
    # ------------------------------------------------------------------
    if args.command == "add":
        transaction = prompt_add(service)
        print(f"[저장 완료] id={transaction.id}")
        return 0

    # ------------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------------
    if args.command == "list":
        count = 0

        # list_transactions()는 generator이므로 한 건씩 받아 바로 출력합니다.
        for transaction in service.list_transactions(args.limit):
            print(format_transaction(transaction))
            count += 1

        if count == 0:
            print("[안내] 거래 데이터가 없습니다.")
        return 0

    # ------------------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------------------
    if args.command == "search":
        count = 0

        # 사용자가 지정하지 않은 검색 옵션은 None으로 전달되어 필터에서 제외됩니다.
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

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------
    if args.command == "summary":
        result = service.summary(args.month, args.top)

        # 거래가 없는 달도 오류가 아니라 명확한 '데이터 없음' 상태로 처리합니다.
        if result["count"] == 0:
            print(f"[안내] {result['month']} 데이터 없음")
            return 0

        print(f"총 수입: {result['income']}원")
        print(f"총 지출: {result['expense']}원")
        print(f"잔액: {result['balance']}원")

        # 예산을 설정한 월에만 예산 관련 정보를 출력합니다.
        if result["budget"] is not None:
            print(f"예산: {result['budget']}원 (사용률 {result['budget_usage']:.1f}%)")
            if result["over_budget"]:
                print("[WARNING] 월 예산을 초과했습니다.")

        print(f"지출 TOP {args.top}")
        # enumerate(..., start=1)로 순위를 1부터 출력합니다.
        for index, (category, amount) in enumerate(result["top"], start=1):
            print(f"{index}) {category} {amount}원")
        return 0

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------
    if args.command == "delete":
        service.delete_transaction(args.transaction_id)
        print(f"[삭제 완료] id={args.transaction_id}")
        return 0

    # ------------------------------------------------------------------
    # BUDGET SET
    # ------------------------------------------------------------------
    if args.command == "budget" and args.budget_command == "set":
        budget = service.set_budget(args.month, args.amount)
        print(f"[저장 완료] {budget.month} 예산 {budget.amount}원")
        return 0

    # ------------------------------------------------------------------
    # CATEGORY
    # ------------------------------------------------------------------
    if args.command == "category":
        if args.category_command == "list":
            for name in service.list_categories():
                print(f"- {name}")
            return 0

        if args.category_command == "add":
            # --name을 주지 않았다면 대화형 input()으로 이름을 받습니다.
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

    # ------------------------------------------------------------------
    # IMPORT
    # ------------------------------------------------------------------
    if args.command == "import":
        result = service.import_csv(Path(args.source))

        # Partial Success 정책이므로 성공/건너뜀 건수를 모두 보여 줍니다.
        print(f"[완료] imported={result.imported}, skipped={result.skipped}")
        for error in result.errors:
            print(f"[SKIP] {error}")
        return 0

    # ------------------------------------------------------------------
    # EXPORT
    # ------------------------------------------------------------------
    if args.command == "export":
        count = service.export_csv(
            Path(args.out),
            month=args.month,
            date_from=args.date_from,
            date_to=args.date_to,
        )
        print(f"[완료] {args.out} ({count} records)")
        return 0

    # argparse의 required subcommand 때문에 보통 여기까지 올 수 없지만,
    # 방어적으로 알 수 없는 상태를 AppError로 처리합니다.
    raise AppError("알 수 없는 명령입니다.", "--help로 사용 가능한 명령을 확인하세요.")
