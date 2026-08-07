from __future__ import annotations

import functools
import sys
from collections.abc import Callable
from typing import ParamSpec

from .exceptions import BudgetError

P = ParamSpec("P")


def cli_guard(func: Callable[P, int]) -> Callable[P, int]:
    """Convert expected failures into stable user messages and non-zero exit codes."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> int:
        try:
            return func(*args, **kwargs)
        except BudgetError as exc:
            print(f"[오류] {exc}", file=sys.stderr)
            print(f"[힌트] {exc.hint}", file=sys.stderr)
            return 2
        except KeyboardInterrupt:
            print("[오류] 작업이 사용자에 의해 취소되었습니다.", file=sys.stderr)
            print("[힌트] 명령을 다시 실행해 주세요.", file=sys.stderr)
            return 130
        except OSError as exc:
            print(f"[오류] 파일 작업에 실패했습니다: {exc}", file=sys.stderr)
            print("[힌트] 파일 경로와 읽기/쓰기 권한을 확인해 주세요.", file=sys.stderr)
            return 3

    return wrapper
