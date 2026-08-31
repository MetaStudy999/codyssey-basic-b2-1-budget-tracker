"""터미널 화면과 키보드 입력을 담당하는 작은 도구 모음입니다.

이 파일은 TUI(Terminal User Interface, 터미널 사용자 인터페이스)에서
필요한 조금 어려운 처리를 한곳에 모아 둡니다.

메뉴 코드가 ANSI 제어문자나 운영체제별 키 입력 방식을 직접 알 필요가 없도록
분리하는 것이 목적입니다.

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
import time
from contextlib import contextmanager
from typing import Iterator


class Key:
    """메뉴에서 사용하는 키 이름을 한곳에 모아 둡니다.

    실제 방향키는 터미널에서 여러 바이트로 전달됩니다.
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


_WINDOWS_ARROW_KEYS = {
    "H": Key.UP,
    "P": Key.DOWN,
    "M": Key.RIGHT,
    "K": Key.LEFT,
}

# Linux/macOS 계열 터미널의 방향키는 보통 ESC로 시작하는 여러 바이트입니다.
# VS Code Terminal, SSH, WSL, OrbStack처럼 중간 계층이 있는 환경에서는
# 세 번째 이후 바이트가 조금 늦게 도착하거나 수정키 정보가 끼어들 수 있습니다.
#
# 예:
#   ESC [ A       -> 위
#   ESC O A       -> 위
#   ESC [ 1 ; 5 A -> Ctrl+위 같은 확장 형식
#
# 따라서 정확히 세 글자만 읽지 않고, 방향을 나타내는 마지막 A/B/C/D까지 읽습니다.
_POSIX_SEQUENCE_TIMEOUT_SECONDS = 0.50
_POSIX_SEQUENCE_MAX_BYTES = 16


def is_interactive_terminal() -> bool:
    """현재 입력과 출력이 실제 대화형 터미널인지 확인합니다."""

    return sys.stdin.isatty() and sys.stdout.isatty()


def supports_color() -> bool:
    """현재 터미널에서 색상을 사용하는 것이 적절한지 판단합니다."""

    if os.environ.get("NO_COLOR") is not None:
        return False

    if os.environ.get("TERM", "").lower() == "dumb":
        return False

    return sys.stdout.isatty()


def paint(text: str, *styles: str) -> str:
    """문자열에 색상/강조를 적용합니다.

    색상을 지원하지 않는 환경에서는 원래 문자열을 그대로 반환합니다.
    """

    if not styles or not supports_color():
        return text

    return "".join(styles) + text + Ansi.RESET


def clear_screen() -> None:
    """터미널 화면을 지우고 커서를 왼쪽 위로 이동합니다."""

    if os.name == "nt":
        os.system("cls")
        return

    print("\033[2J\033[H", end="", flush=True)


def _read_windows_key() -> str:
    """Windows 콘솔에서 키 하나를 읽습니다."""

    import msvcrt

    first = msvcrt.getwch()

    if first in {"\x00", "\xe0"}:
        return _WINDOWS_ARROW_KEYS.get(msvcrt.getwch(), Key.UNKNOWN)

    if first in {"\r", "\n"}:
        return Key.ENTER
    if first == "\x1b":
        return Key.ESC
    if first.lower() == "q":
        return Key.QUIT

    return first


def _decode_posix_sequence(sequence: bytes) -> str:
    """터미널에서 읽은 바이트 묶음을 프로그램의 Key 값으로 바꿉니다.

    이 함수는 입력 장치 자체를 읽지 않고 이미 받은 바이트만 해석합니다.
    따라서 복잡한 방향키 형식을 한곳에서 이해하기 쉽게 관리할 수 있습니다.
    """

    if sequence in {b"\r", b"\n"}:
        return Key.ENTER

    if sequence.lower() == b"q":
        return Key.QUIT

    if sequence == b"\x1b":
        return Key.ESC

    # 일반적인 방향키는 ESC [ 로 시작하고,
    # 일부 터미널은 ESC O 로 시작합니다.
    is_escape_sequence = sequence.startswith((b"\x1b[", b"\x1bO"))

    if is_escape_sequence and sequence[-1:] == b"A":
        return Key.UP
    if is_escape_sequence and sequence[-1:] == b"B":
        return Key.DOWN
    if is_escape_sequence and sequence[-1:] == b"C":
        return Key.RIGHT
    if is_escape_sequence and sequence[-1:] == b"D":
        return Key.LEFT

    # 한 글자 일반 입력은 가능하면 문자열로 돌려줍니다.
    if len(sequence) == 1:
        try:
            return sequence.decode("utf-8")
        except UnicodeDecodeError:
            return Key.UNKNOWN

    return Key.UNKNOWN


def _read_posix_sequence(file_descriptor: int) -> bytes:
    """Linux/macOS 터미널에서 키 한 번에 해당하는 실제 바이트를 읽습니다.

    중요한 점:
        ``sys.stdin.read()``와 ``select(sys.stdin)``을 섞지 않습니다.

    Python의 텍스트 입력 객체는 내부 버퍼를 사용하므로,
    OS에는 더 읽을 데이터가 없어 보여도 Python 버퍼에는 방향키의 다음 문자가
    이미 들어 있을 수 있습니다. 그러면 방향키의 첫 ESC만 읽고 종료키로
    잘못 판단할 수 있습니다.

    여기서는 ``os.read()``와 파일 디스크립터를 직접 사용해
    읽기와 대기 기준을 모두 같은 OS 입력 계층으로 맞춥니다.
    """

    first = os.read(file_descriptor, 1)

    # Esc로 시작하지 않는 키는 한 바이트만으로 충분합니다.
    if first != b"\x1b":
        return first

    sequence = bytearray(first)
    deadline = time.monotonic() + _POSIX_SEQUENCE_TIMEOUT_SECONDS

    while len(sequence) < _POSIX_SEQUENCE_MAX_BYTES:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break

        ready, _, _ = select.select([file_descriptor], [], [], remaining)
        if not ready:
            break

        next_byte = os.read(file_descriptor, 1)
        if not next_byte:
            break

        sequence.extend(next_byte)

        # 방향키의 마지막 바이트 A/B/C/D를 받으면 더 기다릴 필요가 없습니다.
        # 단, ESC 다음에 바로 A가 들어오는 비표준 입력을 방향키로 오인하지 않도록
        # 최소한 ESC + '[' 또는 'O'까지 확인합니다.
        if (
            len(sequence) >= 3
            and bytes(sequence).startswith((b"\x1b[", b"\x1bO"))
            and next_byte in {b"A", b"B", b"C", b"D"}
        ):
            break

    return bytes(sequence)


def _read_posix_key() -> str:
    """Linux/macOS 터미널에서 키 하나를 읽어 의미 있는 Key 값으로 반환합니다."""

    import termios
    import tty

    file_descriptor = sys.stdin.fileno()
    original_settings = termios.tcgetattr(file_descriptor)

    try:
        # raw 모드에서는 Enter를 기다리지 않고 키 입력을 즉시 받을 수 있습니다.
        tty.setraw(file_descriptor)
        sequence = _read_posix_sequence(file_descriptor)
        return _decode_posix_sequence(sequence)
    finally:
        # 어떤 경로로 함수가 끝나더라도 터미널 설정을 원래대로 되돌립니다.
        termios.tcsetattr(file_descriptor, termios.TCSADRAIN, original_settings)


def read_key() -> str:
    """사용자가 누른 키 하나를 읽어 의미가 분명한 값으로 반환합니다.

    반환 예:
        ``Key.UP``, ``Key.DOWN``, ``Key.LEFT``, ``Key.RIGHT``,
        ``Key.ENTER``, ``Key.ESC``, ``Key.QUIT``
    """

    if not is_interactive_terminal():
        raise RuntimeError("방향키 메뉴는 대화형 터미널에서 실행해야 합니다.")

    if os.name == "nt":
        return _read_windows_key()

    return _read_posix_key()


@contextmanager
def hidden_cursor() -> Iterator[None]:
    """메뉴를 표시하는 동안 깜빡이는 커서를 잠시 숨깁니다."""

    if not supports_color():
        yield
        return

    print("\033[?25l", end="", flush=True)
    try:
        yield
    finally:
        print("\033[?25h", end="", flush=True)


@contextmanager
def visible_cursor() -> Iterator[None]:
    """텍스트를 입력하는 동안 터미널 커서를 잠시 다시 보여 줍니다."""

    if not supports_color():
        yield
        return

    print("\033[?25h", end="", flush=True)
    try:
        yield
    finally:
        print("\033[?25l", end="", flush=True)
