"""터미널 화면과 키보드 입력을 담당하는 작은 도구 모음입니다.

이 파일은 TUI(Terminal User Interface, 터미널 사용자 인터페이스)에서
필요한 조금 어려운 처리를 한곳에 모아 둡니다.

메뉴 코드가 ``\033[...`` 같은 제어문자나 운영체제별 키 입력 방식을
직접 알 필요가 없도록 분리하는 것이 목적입니다.

입문자는 우선 다음 함수의 역할만 이해하면 충분합니다.

- ``clear_screen()``: 화면을 깨끗하게 지웁니다.
- ``paint()``: 글자에 색상이나 강조 효과를 붙입니다.
- ``read_key()``: 방향키/Enter/Esc/Q 같은 키를 읽습니다.
- ``hidden_cursor()``: 메뉴를 그리는 동안 커서를 잠시 숨깁니다.
- ``visible_cursor()``: 글자를 입력할 때 커서를 잠시 다시 보여 줍니다.

외부 패키지는 사용하지 않으며 Python 표준 라이브러리만 사용합니다.
"""

from __future__ import annotations

import os
import select
import sys
from contextlib import contextmanager
from typing import Iterator


class Key:
    """메뉴에서 사용하는 키 이름을 한곳에 모아 둡니다.

    실제 방향키는 터미널에서 여러 문자로 전달될 수 있습니다.
    다른 파일에서는 그 복잡한 값을 직접 비교하지 않고
    ``Key.UP``처럼 의미가 분명한 이름을 사용합니다.
    """

    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    ENTER = "ENTER"
    ESC = "ESC"
    QUIT = "QUIT"
    UNKNOWN = "UNKNOWN"


class Ansi:
    """ANSI(터미널 제어 표준) 색상 코드를 읽기 쉬운 이름으로 정의합니다."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    REVERSE = "\033[7m"


# Linux/macOS 방향키는 터미널에 따라 두 가지 대표 형식으로 전달될 수 있습니다.
#
#   ESC [ A   : 일반적인 CSI 형식
#   ESC O A   : 일부 터미널의 SS3 형식
#
# 메뉴 코드에서는 이런 차이를 알 필요가 없도록 모두 Key.UP 같은 값으로 바꿉니다.
_POSIX_ARROW_KEYS = {
    "\x1b[A": Key.UP,
    "\x1b[B": Key.DOWN,
    "\x1b[C": Key.RIGHT,
    "\x1b[D": Key.LEFT,
    "\x1bOA": Key.UP,
    "\x1bOB": Key.DOWN,
    "\x1bOC": Key.RIGHT,
    "\x1bOD": Key.LEFT,
}

_WINDOWS_ARROW_KEYS = {
    "H": Key.UP,
    "P": Key.DOWN,
    "M": Key.RIGHT,
    "K": Key.LEFT,
}


# 방향키는 ESC 문자 하나가 아니라 여러 문자가 연속해서 들어옵니다.
# VS Code 터미널, SSH, WSL, 가상환경에서는 문자 사이에 아주 짧은 지연이 생길 수 있습니다.
# 0.20초 정도 기다리면 Esc 단독 입력과 방향키 입력을 안정적으로 구분할 수 있습니다.
_POSIX_ESCAPE_TIMEOUT_SECONDS = 0.20


def is_interactive_terminal() -> bool:
    """현재 입력과 출력이 실제 대화형 터미널인지 확인합니다.

    방향키 메뉴는 키보드 입력을 한 글자씩 읽어야 하므로,
    파일 리다이렉션이나 자동 테스트 환경에서는 실행하지 않는 편이 안전합니다.
    """

    return sys.stdin.isatty() and sys.stdout.isatty()


def supports_color() -> bool:
    """현재 터미널에서 색상을 사용하는 것이 적절한지 판단합니다."""

    # NO_COLOR 환경변수는 "색상을 사용하지 말아 달라"는 널리 쓰이는 약속입니다.
    if os.environ.get("NO_COLOR") is not None:
        return False

    # TERM=dumb은 최소 기능 터미널을 뜻하므로 색상 제어를 피합니다.
    if os.environ.get("TERM", "").lower() == "dumb":
        return False

    return sys.stdout.isatty()


def paint(text: str, *styles: str) -> str:
    """문자열에 색상/강조를 적용합니다.

    예:
        ``paint("성공", Ansi.GREEN, Ansi.BOLD)``

    색상을 지원하지 않는 환경에서는 원래 문자열을 그대로 반환합니다.
    """

    if not styles or not supports_color():
        return text

    return "".join(styles) + text + Ansi.RESET


def clear_screen() -> None:
    """터미널 화면을 지우고 커서를 왼쪽 위로 이동합니다."""

    if os.name == "nt":
        # Windows 기본 콘솔에서도 확실하게 동작하도록 cls를 사용합니다.
        os.system("cls")
        return

    # POSIX 계열(Linux/macOS)은 ANSI 제어문자로 화면을 지웁니다.
    print("\033[2J\033[H", end="", flush=True)


def _read_windows_key() -> str:
    """Windows 콘솔에서 키 하나를 읽습니다.

    이 함수는 운영체제별 세부 구현이므로 메뉴 코드에서는 직접 호출하지 않습니다.
    """

    import msvcrt  # Windows 표준 라이브러리이며 Windows에서만 불러옵니다.

    first = msvcrt.getwch()

    # 방향키는 첫 문자 뒤에 한 문자가 더 전달됩니다.
    if first in {"\x00", "\xe0"}:
        return _WINDOWS_ARROW_KEYS.get(msvcrt.getwch(), Key.UNKNOWN)

    if first in {"\r", "\n"}:
        return Key.ENTER
    if first == "\x1b":
        return Key.ESC
    if first.lower() == "q":
        return Key.QUIT

    return first


def _has_pending_input(timeout: float) -> bool:
    """지정한 시간 안에 다음 키 입력 문자가 도착하는지 확인합니다.

    방향키의 첫 문자는 Esc와 같기 때문에 바로 종료로 판단하면 안 됩니다.
    잠깐 기다린 뒤 이어지는 문자가 있으면 방향키 시퀀스로 처리합니다.
    """

    return bool(select.select([sys.stdin], [], [], timeout)[0])


def _read_posix_key() -> str:
    """Linux/macOS 터미널에서 키 하나를 읽습니다."""

    # termios와 tty는 POSIX 계열 터미널 제어용 Python 표준 라이브러리입니다.
    # Windows에서 모듈 import 자체가 실패하지 않도록 함수 안에서 불러옵니다.
    import termios
    import tty

    file_descriptor = sys.stdin.fileno()
    original_settings = termios.tcgetattr(file_descriptor)

    try:
        # raw 모드에서는 Enter를 누를 때까지 기다리지 않고 키를 즉시 받을 수 있습니다.
        tty.setraw(file_descriptor)
        first = sys.stdin.read(1)

        if first in {"\r", "\n"}:
            return Key.ENTER
        if first.lower() == "q":
            return Key.QUIT

        # Esc가 아닌 일반 문자는 그대로 반환합니다.
        if first != "\x1b":
            return first

        # 여기부터는 Esc 단독 입력인지 방향키의 시작인지 구분합니다.
        # 방향키라면 ESC 뒤에 '[' 또는 'O', 그리고 A/B/C/D가 차례로 들어옵니다.
        if not _has_pending_input(_POSIX_ESCAPE_TIMEOUT_SECONDS):
            return Key.ESC

        second = sys.stdin.read(1)

        # '[' 또는 'O'가 아니면 우리가 지원하는 방향키 형식이 아닙니다.
        if second not in {"[", "O"}:
            return Key.UNKNOWN

        if not _has_pending_input(_POSIX_ESCAPE_TIMEOUT_SECONDS):
            return Key.UNKNOWN

        third = sys.stdin.read(1)
        sequence = first + second + third
        return _POSIX_ARROW_KEYS.get(sequence, Key.UNKNOWN)
    finally:
        # 프로그램이 중간에 오류가 나더라도 원래 터미널 입력 상태를 반드시 복원합니다.
        termios.tcsetattr(file_descriptor, termios.TCSADRAIN, original_settings)


def read_key() -> str:
    """사용자가 누른 키 하나를 읽어 의미가 분명한 값으로 반환합니다.

    반환 예:
        ``Key.UP``, ``Key.DOWN``, ``Key.ENTER``, ``Key.ESC``, ``Key.QUIT``
    """

    if not is_interactive_terminal():
        raise RuntimeError("방향키 메뉴는 대화형 터미널에서 실행해야 합니다.")

    if os.name == "nt":
        return _read_windows_key()

    return _read_posix_key()


@contextmanager
def hidden_cursor() -> Iterator[None]:
    """메뉴를 표시하는 동안 깜빡이는 커서를 잠시 숨깁니다.

    ``with hidden_cursor():`` 블록이 끝나면 커서를 자동으로 다시 표시합니다.
    따라서 오류나 조기 종료가 발생해도 터미널 커서가 사라진 채 남는 것을 줄일 수 있습니다.
    """

    if not supports_color():
        # 색상 제어를 쓰지 않는 단순 터미널에서는 커서 제어도 하지 않습니다.
        yield
        return

    print("\033[?25l", end="", flush=True)
    try:
        yield
    finally:
        print("\033[?25h", end="", flush=True)


@contextmanager
def visible_cursor() -> Iterator[None]:
    """텍스트를 입력하는 동안 터미널 커서를 잠시 다시 보여 줍니다.

    메인 메뉴는 화면을 깔끔하게 보이게 하려고 커서를 숨기지만,
    날짜·금액·메모처럼 글자를 입력할 때는 현재 입력 위치를 확인할 수 있어야 합니다.

    이 컨텍스트를 빠져나오면 다시 커서를 숨겨 메뉴 화면의 모양을 유지합니다.
    """

    if not supports_color():
        yield
        return

    print("\033[?25h", end="", flush=True)
    try:
        yield
    finally:
        print("\033[?25l", end="", flush=True)
