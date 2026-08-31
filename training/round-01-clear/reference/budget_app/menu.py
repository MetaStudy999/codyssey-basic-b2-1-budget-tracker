"""B2-1 입문자용 방향키 메뉴입니다.

이 모듈은 사용자가 긴 CLI 명령을 외우지 않아도 가계부를 사용할 수 있도록
방향키 중심의 TUI(Terminal User Interface, 터미널 사용자 인터페이스)를 제공합니다.

현재 연결된 실제 기능:

- ↑ / ↓ 방향키로 메뉴 이동
- → 또는 Enter로 메뉴 선택
- Q 또는 Esc로 메인 메뉴 종료
- ANSI 색상으로 현재 선택 항목 강조
- 거래 추가: 종류와 카테고리를 방향키로 선택한 뒤 실제 JSONL에 저장
- 거래 목록: 최근 거래를 최신순 컬러 표로 확인
- 거래 검색: 날짜·종류·카테고리·메모·태그 조건으로 검색
- 거래 수정: 최근 거래를 방향키로 고른 뒤 필요한 값을 수정
- 거래 삭제: 최근 거래를 방향키로 고르고 안전 확인 후 삭제

중요한 설계 원칙:

- 기존 CLI는 그대로 유지합니다.
- 저장/검증/검색/수정/삭제 규칙을 이 파일에서 다시 만들지 않습니다.
- 실제 업무 규칙은 기존 ``BudgetService``를 호출합니다.
- 터미널의 어려운 키 입력 처리는 ``terminal.py``에 맡깁니다.
- 거래가 많아도 화면용 최대 건수만 제너레이터에서 순서대로 받습니다.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date as calendar_date
from pathlib import Path

from .errors import AppError
from .models import Transaction
from .services import BudgetService
from .terminal import (
    Ansi,
    Key,
    clear_screen,
    hidden_cursor,
    is_interactive_terminal,
    paint,
    read_key,
    visible_cursor,
)


# TUI 화면은 한 번에 너무 많은 거래를 보여 주지 않습니다.
# Service의 generator를 끝까지 list로 만들지 않고 필요한 건수까지만 읽습니다.
LIST_DISPLAY_LIMIT = 20
SEARCH_DISPLAY_LIMIT = 50
SELECT_TRANSACTION_LIMIT = 20


@dataclass(frozen=True, slots=True)
class MenuItem:
    """메인 메뉴 한 줄에 필요한 정보를 표현합니다.

    ``action``은 프로그램 내부에서 기능을 구분하는 이름입니다.
    화면에는 사용자가 이해하기 쉬운 ``label``과 ``description``을 보여 줍니다.
    """

    action: str
    label: str
    description: str


@dataclass(frozen=True, slots=True)
class Choice:
    """방향키 선택 화면에서 보여 줄 항목 하나를 표현합니다.

    ``label``은 사용자에게 보여 주는 글자이고,
    ``value``는 실제 Service에 전달할 값입니다.
    """

    label: str
    value: str


# 메뉴는 실제 가계부를 사용하는 순서에 가깝게 배치합니다.
MAIN_MENU_ITEMS = (
    MenuItem("add", "거래 추가", "수입 또는 지출 내역을 새로 기록합니다."),
    MenuItem("list", "거래 목록", "최근 거래 내역을 확인합니다."),
    MenuItem("search", "거래 검색", "날짜·카테고리·종류·메모·태그로 찾습니다."),
    MenuItem("update", "거래 수정", "저장된 거래를 방향키로 골라 내용을 고칩니다."),
    MenuItem("delete", "거래 삭제", "저장된 거래를 방향키로 골라 안전하게 삭제합니다."),
    MenuItem("summary", "월별 요약", "수입·지출·잔액과 지출 순위를 봅니다."),
    MenuItem("budget", "예산 관리", "월 예산을 설정하고 사용률을 확인합니다."),
    MenuItem("category", "카테고리 관리", "카테고리를 추가·조회·삭제합니다."),
    MenuItem("csv", "CSV 가져오기 / 내보내기", "다른 파일과 거래 데이터를 주고받습니다."),
    MenuItem("help", "도움말", "키보드 사용 방법을 확인합니다."),
    MenuItem("exit", "종료", "프로그램을 안전하게 종료합니다."),
)


def move_selection(current: int, direction: int, item_count: int) -> int:
    """현재 선택 위치를 위 또는 아래로 한 칸 이동합니다.

    나머지 연산자(%)를 사용하므로 마지막에서 아래로 가면 첫 항목으로,
    첫 항목에서 위로 가면 마지막 항목으로 자연스럽게 순환합니다.
    """

    if item_count <= 0:
        return 0
    return (current + direction) % item_count


def _header(data_dir: Path | None = None) -> None:
    """화면 상단에 프로그램 제목과 현재 데이터 위치를 출력합니다."""

    print(paint("╭──────────────────────────────────────────────────────────╮", Ansi.CYAN))
    print(paint("  Codyssey B2-1 · Budget Tracker", Ansi.CYAN, Ansi.BOLD))
    print("  나만의 용돈 기입장")
    print(paint("╰──────────────────────────────────────────────────────────╯", Ansi.CYAN))

    if data_dir is not None:
        print(paint(f"  데이터 위치: {data_dir}", Ansi.DIM))
    print()


def _footer() -> None:
    """메인 메뉴 하단에 키보드 사용법을 표시합니다."""

    print()
    print(paint("↑ ↓ 이동   → / Enter 선택   Esc / Q 종료", Ansi.DIM))
    print(paint("현재 단계: 거래 추가 · 목록 · 검색 · 수정 · 삭제 연결", Ansi.YELLOW))


def draw_main_menu(selected_index: int, data_dir: Path) -> None:
    """현재 선택 위치를 기준으로 전체 메인 메뉴를 다시 그립니다."""

    clear_screen()
    _header(data_dir)

    for index, item in enumerate(MAIN_MENU_ITEMS):
        is_selected = index == selected_index

        if is_selected:
            marker = paint("➤", Ansi.CYAN, Ansi.BOLD)
            label = paint(item.label, Ansi.CYAN, Ansi.BOLD)
        else:
            marker = " "
            label = item.label

        print(f" {marker} {label}")

        if is_selected:
            print("     " + paint(item.description, Ansi.DIM))

    _footer()


def wait_for_return() -> None:
    """사용자가 내용을 읽을 시간을 준 뒤 이전 메뉴로 돌아갑니다."""

    print()
    print(paint("Enter 또는 ← 를 누르면 메뉴로 돌아갑니다.", Ansi.DIM))

    while True:
        key = read_key()
        if key in {Key.ENTER, Key.LEFT, Key.ESC, Key.QUIT}:
            return


def show_help() -> None:
    """입문자가 방향키와 안전한 삭제 동작을 바로 이해하도록 도움말을 보여 줍니다."""

    clear_screen()
    print(paint("B2-1 메뉴 도움말", Ansi.CYAN, Ansi.BOLD))
    print()
    print("  ↑        위 메뉴로 이동")
    print("  ↓        아래 메뉴로 이동")
    print("  →        현재 메뉴 선택")
    print("  Enter    현재 메뉴 선택")
    print("  ←        이전 화면으로 이동")
    print("  Esc      이전 화면 또는 취소")
    print("  Q        메인 메뉴에서는 프로그램 종료")
    print()
    print("  거래 수정/삭제에서는 ID를 외워 입력하지 않습니다.")
    print("  최근 거래 목록에서 ↑ ↓ 방향키로 원하는 거래를 고릅니다.")
    print("  삭제 확인 화면의 기본 선택은 '취소'이므로 Enter를 잘못 눌러도 바로 삭제되지 않습니다.")
    print()
    print(paint("명령어를 외우지 않아도 방향키 중심으로 사용할 수 있습니다.", Ansi.GREEN))
    wait_for_return()


def choose_option(
    title: str,
    choices: Sequence[Choice],
    *,
    description: str = "",
    initial_index: int = 0,
) -> str | None:
    """방향키로 항목 하나를 선택하고 그 항목의 실제 값을 반환합니다.

    - Enter/→: 선택 항목의 ``value`` 반환
    - ←/Esc/Q: 선택을 취소하고 ``None`` 반환

    ``initial_index``는 처음 강조할 항목입니다.
    삭제처럼 실수 방지가 중요한 화면에서는 '취소'를 0번에 놓고
    기본값을 0으로 두면 Enter를 잘못 눌러도 안전하게 취소됩니다.
    """

    if not choices:
        return None

    selected_index = max(0, min(initial_index, len(choices) - 1))

    while True:
        clear_screen()
        _header()
        print(paint(title, Ansi.CYAN, Ansi.BOLD))

        if description:
            print()
            for line in description.splitlines():
                print(f"  {line}")

        print()

        for index, choice in enumerate(choices):
            if index == selected_index:
                marker = paint("➤", Ansi.CYAN, Ansi.BOLD)
                label = paint(choice.label, Ansi.CYAN, Ansi.BOLD)
            else:
                marker = " "
                label = choice.label
            print(f" {marker} {label}")

        print()
        print(paint("↑ ↓ 이동   → / Enter 선택   ← / Esc 취소", Ansi.DIM))

        key = read_key()

        if key == Key.UP:
            selected_index = move_selection(selected_index, -1, len(choices))
            continue

        if key == Key.DOWN:
            selected_index = move_selection(selected_index, 1, len(choices))
            continue

        if key in {Key.LEFT, Key.ESC, Key.QUIT}:
            return None

        if key in {Key.RIGHT, Key.ENTER}:
            return choices[selected_index].value


def ask_text(
    title: str,
    prompt: str,
    *,
    default: str | None = None,
    optional: bool = False,
) -> str:
    """날짜·금액·메모처럼 자유롭게 입력해야 하는 값 하나를 받습니다."""

    clear_screen()
    _header()
    print(paint(title, Ansi.CYAN, Ansi.BOLD))
    print()

    if optional:
        print(paint("선택 항목입니다. 필요 없으면 Enter만 누르세요.", Ansi.DIM))

    if default is not None:
        print(paint(f"기본값: {default} (그대로 쓰려면 Enter)", Ansi.DIM))

    print()

    with visible_cursor():
        value = input(f"{prompt}: ").strip()

    if not value and default is not None:
        return default

    return value


def ask_edit_text(
    title: str,
    prompt: str,
    current: str,
    *,
    allow_clear: bool = False,
) -> str:
    """수정 화면에서 현재 값을 보여 주고 새 값을 입력받습니다.

    그냥 Enter를 누르면 기존 값을 유지합니다.

    메모·태그처럼 빈 값이 허용되는 항목은 ``allow_clear=True``로 호출합니다.
    이 경우 하이픈 한 글자(``-``)를 입력하면 값을 비울 수 있습니다.
    """

    clear_screen()
    _header()
    print(paint(title, Ansi.CYAN, Ansi.BOLD))
    print()
    print(f"현재 값: {current or '(없음)'}")
    print(paint("변경하지 않으려면 Enter만 누르세요.", Ansi.DIM))

    if allow_clear:
        print(paint("내용을 모두 지우려면 - 한 글자를 입력하세요.", Ansi.DIM))

    print()

    with visible_cursor():
        value = input(f"{prompt}: ").strip()

    if not value:
        return current

    if allow_clear and value == "-":
        return ""

    return value


def show_notice(title: str, message: str, *, color: str = Ansi.YELLOW) -> None:
    """성공·취소·안내처럼 사용자가 확인해야 하는 메시지를 보여 줍니다."""

    clear_screen()
    print(paint(title, color, Ansi.BOLD))
    print()
    print(message)
    wait_for_return()


def _friendly_tui_hint(error: AppError) -> str:
    """CLI 용어가 낯선 오류에는 TUI용 추가 설명을 제공합니다."""

    if error.message == "--from 날짜가 --to 날짜보다 늦습니다.":
        return (
            "시작일(--from)은 종료일(--to)과 같거나 더 이른 날짜여야 합니다.\n"
            "예: 시작일 2026-08-01 / 종료일 2026-08-31"
        )

    return error.hint


def show_app_error(error: AppError) -> None:
    """Service에서 발생한 예상 가능한 오류를 입문자용 형식으로 보여 줍니다."""

    clear_screen()
    print(paint("입력 내용을 확인해 주세요", Ansi.RED, Ansi.BOLD))
    print()
    print(paint("[오류]", Ansi.RED, Ansi.BOLD), error.message)
    print(paint("[힌트]", Ansi.YELLOW, Ansi.BOLD), _friendly_tui_hint(error))
    wait_for_return()


def _shorten(text: str, width: int) -> str:
    """표가 너무 넓어지지 않도록 긴 문자열을 읽기 좋게 줄입니다."""

    if len(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    return text[: width - 1] + "…"


def _take_transactions(source: Iterable[Transaction], limit: int) -> list[Transaction]:
    """제너레이터에서 화면에 필요한 거래만 순서대로 가져옵니다."""

    result: list[Transaction] = []

    for transaction in source:
        result.append(transaction)
        if len(result) >= limit:
            break

    return result


def _amount_text(transaction: Transaction) -> str:
    """수입은 +, 지출은 - 기호를 붙여 금액의 의미를 즉시 알 수 있게 합니다."""

    sign = "+" if transaction.type == "income" else "-"
    return f"{sign}{transaction.amount:,}원"


def _transaction_details(transaction: Transaction) -> str:
    """거래 한 건의 모든 주요 값을 확인 화면용 여러 줄 문자열로 만듭니다."""

    tags = ",".join(transaction.tags) if transaction.tags else "(없음)"

    return "\n".join(
        (
            f"ID         : {transaction.id}",
            f"날짜       : {transaction.date}",
            f"종류       : {transaction.type}",
            f"카테고리   : {transaction.category}",
            f"금액       : {transaction.amount:,}원",
            f"메모       : {transaction.memo or '(없음)'}",
            f"태그       : {tags}",
        )
    )


def _transaction_choice_label(transaction: Transaction) -> str:
    """거래 선택 메뉴 한 줄을 짧고 구분하기 쉬운 형태로 만듭니다."""

    type_label = "수입" if transaction.type == "income" else "지출"
    memo = _shorten(transaction.memo or "-", 16)

    return (
        f"{transaction.date} | {type_label:<2} | "
        f"{_shorten(transaction.category, 10):<10} | "
        f"{transaction.amount:>10,}원 | {memo}"
    )


def show_transactions_table(
    title: str,
    transactions: Sequence[Transaction],
    *,
    note: str = "",
) -> None:
    """거래 목록을 외부 라이브러리 없이 간단한 컬러 표로 출력합니다."""

    clear_screen()
    print(paint(title, Ansi.CYAN, Ansi.BOLD))
    print()

    if note:
        print(paint(note, Ansi.DIM))
        print()

    if not transactions:
        print(paint("[안내] 조건에 맞는 거래가 없습니다.", Ansi.YELLOW))
        wait_for_return()
        return

    print(paint("─" * 94, Ansi.DIM))
    print(f"{'ID':<8} {'날짜':<10} {'type':<8} {'카테고리':<14} {'금액':>14}  메모 / 태그")
    print(paint("─" * 94, Ansi.DIM))

    for transaction in transactions:
        memo = transaction.memo or "-"

        if transaction.tags:
            tags = ",".join(transaction.tags)
            memo = f"{memo} [{tags}]"

        amount = _amount_text(transaction)
        amount_color = Ansi.GREEN if transaction.type == "income" else Ansi.RED
        type_color = Ansi.GREEN if transaction.type == "income" else Ansi.YELLOW

        id_cell = _shorten(transaction.id, 8)
        category_cell = _shorten(transaction.category, 14)
        memo_cell = _shorten(memo, 30)

        print(
            f"{id_cell:<8} "
            f"{transaction.date:<10} "
            f"{paint(f'{transaction.type:<8}', type_color)} "
            f"{category_cell:<14} "
            f"{paint(f'{amount:>14}', amount_color, Ansi.BOLD)}  "
            f"{memo_cell}"
        )

    print(paint("─" * 94, Ansi.DIM))
    print(paint(f"표시된 거래: {len(transactions)}건", Ansi.DIM))
    wait_for_return()


def select_transaction(service: BudgetService, title: str) -> Transaction | None:
    """최근 거래 중 한 건을 방향키로 선택합니다.

    사용자가 거래 ID를 외워 직접 입력하지 않도록 하는 것이 목적입니다.
    """

    try:
        transactions = _take_transactions(
            service.list_transactions(SELECT_TRANSACTION_LIMIT),
            SELECT_TRANSACTION_LIMIT,
        )
    except AppError as error:
        show_app_error(error)
        return None

    if not transactions:
        show_notice(
            title,
            "선택할 거래가 없습니다.\n먼저 '거래 추가'에서 거래를 한 건 이상 저장해 주세요.",
        )
        return None

    choices = tuple(
        Choice(_transaction_choice_label(transaction), transaction.id)
        for transaction in transactions
    )

    selected_id = choose_option(
        title,
        choices,
        description=(
            f"최근 거래 최대 {SELECT_TRANSACTION_LIMIT}건입니다.\n"
            "↑ ↓ 로 거래를 고른 뒤 Enter를 누르세요."
        ),
    )

    if selected_id is None:
        return None

    for transaction in transactions:
        if transaction.id == selected_id:
            return transaction

    return None


def run_add_transaction(service: BudgetService) -> None:
    """방향키와 쉬운 입력 화면으로 새 거래 한 건을 저장합니다."""

    today = calendar_date.today().isoformat()
    date_value = ask_text("1/6 · 날짜", "날짜(YYYY-MM-DD)", default=today)

    type_value = choose_option(
        "2/6 · 거래 종류",
        (
            Choice("지출 (expense)", "expense"),
            Choice("수입 (income)", "income"),
        ),
        description="↑ ↓ 방향키로 선택한 뒤 Enter를 누르세요.",
    )

    if type_value is None:
        show_notice("거래 추가 취소", "거래를 저장하지 않고 메인 메뉴로 돌아갑니다.")
        return

    categories = service.list_categories()
    category_value = choose_option(
        "3/6 · 카테고리",
        tuple(Choice(name, name) for name in categories),
        description="등록되어 있는 카테고리 중 하나를 선택하세요.",
    )

    if category_value is None:
        show_notice("거래 추가 취소", "거래를 저장하지 않고 메인 메뉴로 돌아갑니다.")
        return

    amount_value = ask_text("4/6 · 금액", "금액(0보다 큰 정수)")
    memo_value = ask_text("5/6 · 메모", "메모", optional=True)
    tags_value = ask_text("6/6 · 태그", "태그(여러 개면 쉼표로 구분)", optional=True)

    confirmation_text = "\n".join(
        (
            f"날짜       : {date_value}",
            f"종류       : {type_value}",
            f"카테고리   : {category_value}",
            f"금액       : {amount_value}",
            f"메모       : {memo_value or '(없음)'}",
            f"태그       : {tags_value or '(없음)'}",
        )
    )

    confirmation = choose_option(
        "이 거래를 저장할까요?",
        (Choice("저장", "save"), Choice("취소", "cancel")),
        description=confirmation_text,
    )

    if confirmation != "save":
        show_notice("거래 추가 취소", "거래를 저장하지 않고 메인 메뉴로 돌아갑니다.")
        return

    try:
        transaction = service.add_transaction(
            date=date_value,
            type=type_value,
            category=category_value,
            amount=amount_value,
            memo=memo_value,
            tags=tags_value,
        )
    except AppError as error:
        show_app_error(error)
        return

    show_notice(
        "거래 저장 완료",
        "새 거래가 정상적으로 저장되었습니다.\n\n" + _transaction_details(transaction),
        color=Ansi.GREEN,
    )


def run_list_transactions(service: BudgetService) -> None:
    """최근 거래를 최신순으로 최대 20건 보여 줍니다."""

    try:
        transactions = _take_transactions(
            service.list_transactions(LIST_DISPLAY_LIMIT),
            LIST_DISPLAY_LIMIT,
        )
    except AppError as error:
        show_app_error(error)
        return

    show_transactions_table(
        "최근 거래 목록",
        transactions,
        note=f"최신순 최대 {LIST_DISPLAY_LIMIT}건을 보여 줍니다.",
    )


def run_search_transactions(service: BudgetService) -> None:
    """입문자용 단계별 화면으로 검색 조건을 받고 결과를 표시합니다."""

    date_from = ask_text("1/6 · 검색 시작일", "시작일(YYYY-MM-DD)", optional=True)
    date_to = ask_text("2/6 · 검색 종료일", "종료일(YYYY-MM-DD)", optional=True)

    type_value = choose_option(
        "3/6 · 거래 종류",
        (
            Choice("전체 (조건 없음)", ""),
            Choice("지출 (expense)", "expense"),
            Choice("수입 (income)", "income"),
        ),
        description="종류를 제한하지 않으려면 '전체'를 선택하세요.",
    )

    if type_value is None:
        show_notice("검색 취소", "검색하지 않고 메인 메뉴로 돌아갑니다.")
        return

    category_choices = [Choice("전체 (조건 없음)", "")]
    category_choices.extend(Choice(name, name) for name in service.list_categories())

    category_value = choose_option(
        "4/6 · 카테고리",
        tuple(category_choices),
        description="카테고리를 제한하지 않으려면 '전체'를 선택하세요.",
    )

    if category_value is None:
        show_notice("검색 취소", "검색하지 않고 메인 메뉴로 돌아갑니다.")
        return

    query_value = ask_text("5/6 · 메모 검색어", "메모에 포함된 단어", optional=True)
    tag_value = ask_text("6/6 · 태그", "태그 하나", optional=True)

    criteria_lines = (
        f"시작일     : {date_from or '전체'}",
        f"종료일     : {date_to or '전체'}",
        f"종류       : {type_value or '전체'}",
        f"카테고리   : {category_value or '전체'}",
        f"메모       : {query_value or '전체'}",
        f"태그       : {tag_value or '전체'}",
    )

    confirmation = choose_option(
        "이 조건으로 검색할까요?",
        (Choice("검색", "search"), Choice("취소", "cancel")),
        description="\n".join(criteria_lines),
    )

    if confirmation != "search":
        show_notice("검색 취소", "검색하지 않고 메인 메뉴로 돌아갑니다.")
        return

    try:
        source = service.search_transactions(
            date_from=date_from or None,
            date_to=date_to or None,
            category=category_value or None,
            type=type_value or None,
            query=query_value or None,
            tag=tag_value or None,
        )
        transactions = _take_transactions(source, SEARCH_DISPLAY_LIMIT)
    except AppError as error:
        show_app_error(error)
        return

    show_transactions_table(
        "거래 검색 결과",
        transactions,
        note=(
            f"최신순 최대 {SEARCH_DISPLAY_LIMIT}건 표시 · "
            f"종류={type_value or '전체'} · 카테고리={category_value or '전체'}"
        ),
    )


def run_update_transaction(service: BudgetService) -> None:
    """거래를 방향키로 고른 뒤 필요한 내용을 수정합니다.

    화면에서 값을 바꾸는 동안에는 파일을 수정하지 않습니다.
    마지막 확인에서 저장해야 기존 ``BudgetService.update_transaction()``을 호출합니다.
    """

    transaction = select_transaction(service, "수정할 거래를 선택하세요")

    if transaction is None:
        return

    edited_date = transaction.date
    edited_type = transaction.type
    edited_category = transaction.category
    edited_amount = str(transaction.amount)
    edited_memo = transaction.memo
    edited_tags = ",".join(transaction.tags)

    while True:
        draft_text = "\n".join(
            (
                f"ID         : {transaction.id}",
                f"날짜       : {edited_date}",
                f"종류       : {edited_type}",
                f"카테고리   : {edited_category}",
                f"금액       : {edited_amount}원",
                f"메모       : {edited_memo or '(없음)'}",
                f"태그       : {edited_tags or '(없음)'}",
            )
        )

        field = choose_option(
            "수정할 항목을 선택하세요",
            (
                Choice("날짜 수정", "date"),
                Choice("종류 수정", "type"),
                Choice("카테고리 수정", "category"),
                Choice("금액 수정", "amount"),
                Choice("메모 수정", "memo"),
                Choice("태그 수정", "tags"),
                Choice("변경 내용 저장", "save"),
                Choice("수정 취소", "cancel"),
            ),
            description=draft_text,
        )

        if field is None or field == "cancel":
            show_notice("거래 수정 취소", "변경 내용을 저장하지 않고 메인 메뉴로 돌아갑니다.")
            return

        if field == "date":
            edited_date = ask_edit_text("날짜 수정", "새 날짜(YYYY-MM-DD)", edited_date)
            continue

        if field == "type":
            new_type = choose_option(
                "거래 종류 수정",
                (Choice("지출 (expense)", "expense"), Choice("수입 (income)", "income")),
                description=f"현재 값: {edited_type}",
            )
            if new_type is not None:
                edited_type = new_type
            continue

        if field == "category":
            new_category = choose_option(
                "카테고리 수정",
                tuple(Choice(name, name) for name in service.list_categories()),
                description=f"현재 값: {edited_category}",
            )
            if new_category is not None:
                edited_category = new_category
            continue

        if field == "amount":
            edited_amount = ask_edit_text("금액 수정", "새 금액(0보다 큰 정수)", edited_amount)
            continue

        if field == "memo":
            edited_memo = ask_edit_text(
                "메모 수정",
                "새 메모",
                edited_memo,
                allow_clear=True,
            )
            continue

        if field == "tags":
            edited_tags = ask_edit_text(
                "태그 수정",
                "새 태그(여러 개면 쉼표로 구분)",
                edited_tags,
                allow_clear=True,
            )
            continue

        if field == "save":
            break

    final_text = "\n".join(
        (
            f"ID         : {transaction.id}",
            f"날짜       : {edited_date}",
            f"종류       : {edited_type}",
            f"카테고리   : {edited_category}",
            f"금액       : {edited_amount}원",
            f"메모       : {edited_memo or '(없음)'}",
            f"태그       : {edited_tags or '(없음)'}",
        )
    )

    confirmation = choose_option(
        "변경 내용을 저장할까요?",
        (
            Choice("취소 — 원래 거래 유지", "cancel"),
            Choice("저장 — 변경 내용 적용", "save"),
        ),
        description=final_text,
        initial_index=0,
    )

    if confirmation != "save":
        show_notice("거래 수정 취소", "변경 내용을 저장하지 않았습니다.")
        return

    try:
        updated = service.update_transaction(
            transaction.id,
            date=edited_date,
            type=edited_type,
            category=edited_category,
            amount=edited_amount,
            memo=edited_memo,
            tags=edited_tags,
        )
    except AppError as error:
        show_app_error(error)
        return

    show_notice(
        "거래 수정 완료",
        "변경 내용이 정상적으로 저장되었습니다.\n\n" + _transaction_details(updated),
        color=Ansi.GREEN,
    )


def run_delete_transaction(service: BudgetService) -> None:
    """거래를 방향키로 고른 뒤 확인을 거쳐 안전하게 삭제합니다.

    삭제는 되돌리기 어려운 작업이므로 최종 확인 화면의 기본 선택을
    반드시 '취소'로 둡니다. 사용자가 Enter를 실수로 눌러도 삭제되지 않습니다.
    """

    transaction = select_transaction(service, "삭제할 거래를 선택하세요")

    if transaction is None:
        return

    confirmation = choose_option(
        "정말 이 거래를 삭제할까요?",
        (
            Choice("취소 — 거래를 그대로 유지", "cancel"),
            Choice("삭제 — 이 거래를 영구 삭제", "delete"),
        ),
        description=(
            _transaction_details(transaction)
            + "\n\n삭제 후에는 이 메뉴에서 자동으로 복구할 수 없습니다."
        ),
        initial_index=0,
    )

    if confirmation != "delete":
        show_notice("거래 삭제 취소", "거래를 삭제하지 않았습니다.")
        return

    try:
        service.delete_transaction(transaction.id)
    except AppError as error:
        show_app_error(error)
        return

    show_notice(
        "거래 삭제 완료",
        (
            f"선택한 거래를 삭제했습니다.\n\n"
            f"ID         : {transaction.id}\n"
            f"날짜       : {transaction.date}\n"
            f"금액       : {transaction.amount:,}원"
        ),
        color=Ansi.GREEN,
    )


def show_selected_item(item: MenuItem) -> None:
    """아직 연결하지 않은 기능을 선택했을 때 현재 진행 상태를 설명합니다."""

    clear_screen()
    print(paint(item.label, Ansi.CYAN, Ansi.BOLD))
    print()
    print(item.description)
    print()
    print(paint("[준비 상태]", Ansi.YELLOW, Ansi.BOLD), end=" ")
    print("이 기능은 다음 단계에서 기존 BudgetService와 연결합니다.")
    wait_for_return()


def run_menu(data_dir: Path | None = None) -> int:
    """방향키 기반 메인 메뉴를 실행합니다.

    ``data_dir``을 주지 않으면 기존 CLI와 같은 ``./data``를 사용합니다.
    """

    if not is_interactive_terminal():
        print("[오류] 방향키 메뉴는 실제 터미널에서 실행해야 합니다.")
        print("[힌트] Ubuntu/macOS/Windows Terminal의 대화형 셸에서 다시 실행해 주세요.")
        return 2

    selected_data_dir = data_dir or Path("./data")
    service = BudgetService(selected_data_dir)
    selected_index = 0

    with hidden_cursor():
        while True:
            draw_main_menu(selected_index, selected_data_dir)
            key = read_key()

            if key == Key.UP:
                selected_index = move_selection(selected_index, -1, len(MAIN_MENU_ITEMS))
                continue

            if key == Key.DOWN:
                selected_index = move_selection(selected_index, 1, len(MAIN_MENU_ITEMS))
                continue

            if key in {Key.QUIT, Key.ESC}:
                break

            if key not in {Key.RIGHT, Key.ENTER}:
                continue

            selected_item = MAIN_MENU_ITEMS[selected_index]

            if selected_item.action == "exit":
                break
            if selected_item.action == "help":
                show_help()
                continue
            if selected_item.action == "add":
                run_add_transaction(service)
                continue
            if selected_item.action == "list":
                run_list_transactions(service)
                continue
            if selected_item.action == "search":
                run_search_transactions(service)
                continue
            if selected_item.action == "update":
                run_update_transaction(service)
                continue
            if selected_item.action == "delete":
                run_delete_transaction(service)
                continue

            show_selected_item(selected_item)

    clear_screen()
    print(paint("B2-1 Budget Tracker를 종료했습니다.", Ansi.GREEN))
    return 0


if __name__ == "__main__":
    # 기존 ``python -m budget_app`` 평가용 CLI는 아직 변경하지 않습니다.
    # 새 메뉴는 다음 명령으로 독립 실행합니다.
    #
    #   python -m budget_app.menu
    #
    raise SystemExit(run_menu())
