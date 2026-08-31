"""B2-1 입문자용 방향키 메뉴의 첫 번째 버전입니다.

이번 단계의 목표는 '기능 구현'이 아니라 '메뉴 이동 구조'를 안전하게 만드는 것입니다.
기존 CLI(Command Line Interface, 명령줄 인터페이스)는 전혀 변경하지 않습니다.

현재 할 수 있는 일:

- ↑ / ↓ 방향키로 메뉴 이동
- → 또는 Enter로 메뉴 선택
- Q 또는 Esc로 종료
- ANSI 색상으로 현재 선택 항목 강조
- 도움말 화면 확인

다음 단계에서 각 메뉴를 기존 ``BudgetService`` 기능과 하나씩 연결합니다.
"""

from __future__ import annotations

from dataclasses import dataclass

from .terminal import Ansi, Key, clear_screen, hidden_cursor, is_interactive_terminal, paint, read_key


@dataclass(frozen=True, slots=True)
class MenuItem:
    """메인 메뉴 한 줄에 필요한 정보를 표현합니다.

    ``action``은 나중에 실제 기능과 연결할 때 사용하는 내부 이름입니다.
    화면에는 사용자가 이해하기 쉬운 ``label``과 ``description``만 보여 줍니다.
    """

    action: str
    label: str
    description: str


# 메뉴의 순서는 사용자가 실제 가계부를 사용하는 흐름에 가깝게 배치했습니다.
MAIN_MENU_ITEMS = (
    MenuItem("add", "거래 추가", "수입 또는 지출 내역을 새로 기록합니다."),
    MenuItem("list", "거래 목록", "최근 거래 내역을 확인합니다."),
    MenuItem("search", "거래 검색", "날짜·카테고리·종류·메모·태그로 찾습니다."),
    MenuItem("update", "거래 수정", "저장된 거래의 내용을 고칩니다."),
    MenuItem("delete", "거래 삭제", "필요 없는 거래를 삭제합니다."),
    MenuItem("summary", "월별 요약", "수입·지출·잔액과 지출 순위를 봅니다."),
    MenuItem("budget", "예산 관리", "월 예산을 설정하고 사용률을 확인합니다."),
    MenuItem("category", "카테고리 관리", "카테고리를 추가·조회·삭제합니다."),
    MenuItem("csv", "CSV 가져오기 / 내보내기", "다른 파일과 거래 데이터를 주고받습니다."),
    MenuItem("help", "도움말", "키보드 사용 방법을 확인합니다."),
    MenuItem("exit", "종료", "프로그램을 안전하게 종료합니다."),
)


def move_selection(current: int, direction: int, item_count: int) -> int:
    """현재 메뉴 선택 위치를 위 또는 아래로 한 칸 이동합니다.

    ``direction``은 위로 이동할 때 -1, 아래로 이동할 때 1을 사용합니다.

    나머지 연산자(%)를 사용하기 때문에 마지막 메뉴에서 아래로 이동하면
    첫 메뉴로 돌아가고, 첫 메뉴에서 위로 이동하면 마지막 메뉴로 이동합니다.
    """

    if item_count <= 0:
        return 0

    return (current + direction) % item_count


def _header() -> None:
    """메인 메뉴 상단 제목을 출력합니다."""

    print(paint("╭──────────────────────────────────────────────╮", Ansi.CYAN))
    print(paint("  Codyssey B2-1 · Budget Tracker", Ansi.CYAN, Ansi.BOLD))
    print("  나만의 용돈 기입장")
    print(paint("╰──────────────────────────────────────────────╯", Ansi.CYAN))
    print()


def _footer() -> None:
    """메뉴 하단에 키보드 사용법을 짧게 표시합니다."""

    help_text = "↑ ↓ 이동   → / Enter 선택   Esc / Q 종료"
    print()
    print(paint(help_text, Ansi.DIM))
    print(paint("현재 단계: 방향키 메뉴 기반 구조 확인", Ansi.YELLOW))


def draw_main_menu(selected_index: int) -> None:
    """현재 선택 위치를 기준으로 전체 메인 메뉴를 다시 그립니다."""

    clear_screen()
    _header()

    for index, item in enumerate(MAIN_MENU_ITEMS):
        is_selected = index == selected_index

        if is_selected:
            # 선택된 메뉴는 화살표와 청록색 굵은 글씨로 강조합니다.
            marker = paint("➤", Ansi.CYAN, Ansi.BOLD)
            label = paint(item.label, Ansi.CYAN, Ansi.BOLD)
        else:
            marker = " "
            label = item.label

        print(f" {marker} {label}")

        # 설명은 메뉴 이름보다 한 단계 약하게 보여 화면의 우선순위를 만듭니다.
        if is_selected:
            print("     " + paint(item.description, Ansi.DIM))

    _footer()


def wait_for_return() -> None:
    """사용자가 확인할 시간을 준 뒤 메인 메뉴로 돌아갑니다."""

    print()
    print(paint("Enter 또는 ← 를 누르면 메뉴로 돌아갑니다.", Ansi.DIM))

    while True:
        key = read_key()
        if key in {Key.ENTER, Key.LEFT, Key.ESC}:
            return
        if key == Key.QUIT:
            return


def show_help() -> None:
    """입문자가 방향키를 바로 이해할 수 있도록 도움말을 보여 줍니다."""

    clear_screen()
    print(paint("B2-1 메뉴 도움말", Ansi.CYAN, Ansi.BOLD))
    print()
    print("  ↑        위 메뉴로 이동")
    print("  ↓        아래 메뉴로 이동")
    print("  →        현재 메뉴 선택")
    print("  Enter    현재 메뉴 선택")
    print("  ←        이전 화면으로 이동 (다음 단계에서 하위 메뉴에 사용)")
    print("  Esc      이전 화면 또는 종료")
    print("  Q        프로그램 종료")
    print()
    print(paint("명령어를 외우지 않아도 방향키 중심으로 사용할 수 있게 만드는 중입니다.", Ansi.GREEN))
    wait_for_return()


def show_selected_item(item: MenuItem) -> None:
    """아직 기능 연결 전인 메뉴를 선택했을 때 현재 상태를 설명합니다."""

    clear_screen()
    print(paint(item.label, Ansi.CYAN, Ansi.BOLD))
    print()
    print(item.description)
    print()
    print(paint("[준비 상태]", Ansi.YELLOW, Ansi.BOLD), end=" ")
    print("이번 단계에서는 방향키 이동만 먼저 검증합니다.")
    print("다음 단계에서 기존 BudgetService 기능과 이 메뉴를 연결합니다.")
    wait_for_return()


def run_menu() -> int:
    """방향키 기반 메인 메뉴를 실행합니다.

    반환값 0은 사용자가 정상적으로 프로그램을 종료했다는 뜻입니다.
    대화형 터미널이 아닌 환경에서는 2를 반환합니다.
    """

    if not is_interactive_terminal():
        print("[오류] 방향키 메뉴는 실제 터미널에서 실행해야 합니다.")
        print("[힌트] Ubuntu/macOS/Windows Terminal의 대화형 셸에서 다시 실행해 주세요.")
        return 2

    selected_index = 0

    # 메뉴 실행 중에는 커서를 숨겨 화면이 덜 흔들리게 보이도록 합니다.
    # with 블록을 빠져나오면 terminal.py가 커서를 자동으로 복원합니다.
    with hidden_cursor():
        while True:
            draw_main_menu(selected_index)
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
                # 메뉴에서 사용하지 않는 키는 조용히 무시합니다.
                continue

            selected_item = MAIN_MENU_ITEMS[selected_index]

            if selected_item.action == "exit":
                break

            if selected_item.action == "help":
                show_help()
                continue

            show_selected_item(selected_item)

    clear_screen()
    print(paint("B2-1 Budget Tracker를 종료했습니다.", Ansi.GREEN))
    return 0


if __name__ == "__main__":
    # 이번 단계에서는 기존 ``python -m budget_app`` 동작을 변경하지 않습니다.
    # 아래 명령으로 새 메뉴만 독립적으로 시험할 수 있습니다.
    #
    #   python -m budget_app.menu
    #
    raise SystemExit(run_menu())
