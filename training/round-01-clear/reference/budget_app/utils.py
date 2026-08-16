from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Callable, Generator, Iterable
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, ParamSpec, TypeVar

from .errors import AppError

P = ParamSpec("P")
R = TypeVar("R")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def handle_cli_errors(func: Callable[P, int]) -> Callable[P, int]:
    """Convert expected/runtime failures into friendly messages and non-zero exits."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> int:
        try:
            return func(*args, **kwargs)
        except AppError as exc:
            print(f"[오류] {exc.message}", file=sys.stderr)
            print(f"[힌트] {exc.hint}", file=sys.stderr)
            return 2
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"[오류] {exc}", file=sys.stderr)
            print("[힌트] 입력값, 파일 경로와 저장 데이터 형식을 확인해 주세요.", file=sys.stderr)
            return 2
        except Exception as exc:  # Mission rule: no traceback to the user.
            print(f"[오류] 처리 중 예상하지 못한 문제가 발생했습니다: {exc}", file=sys.stderr)
            print("[힌트] 입력값과 데이터 파일 상태를 확인한 뒤 다시 실행해 주세요.", file=sys.stderr)
            return 2

    return wrapper


def validate_date(value: str) -> str:
    if not DATE_RE.match(value):
        raise AppError("날짜 형식이 올바르지 않습니다.", "YYYY-MM-DD 형식으로 입력하세요. 예: 2026-08-16")
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise AppError("존재하지 않는 날짜입니다.", "실제 달력에 존재하는 YYYY-MM-DD 날짜를 입력하세요.") from exc
    return value


def validate_month(value: str) -> str:
    if not MONTH_RE.match(value):
        raise AppError("월 형식이 올바르지 않습니다.", "YYYY-MM 형식으로 입력하세요. 예: 2026-08")
    try:
        datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise AppError("존재하지 않는 월입니다.", "01~12 범위의 월을 입력하세요.") from exc
    return value


def positive_int(value: str | int, field_name: str = "금액") -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise AppError(f"{field_name}은 정수여야 합니다.", "0보다 큰 정수를 입력하세요.") from exc
    if number <= 0:
        raise AppError(f"{field_name}은 0보다 커야 합니다.", "양의 정수를 입력하세요.")
    return number


def validate_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"income", "expense"}:
        raise AppError("type은 income 또는 expense여야 합니다.", "income 또는 expense 중 하나를 입력하세요.")
    return normalized


def parse_tags(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = value.split(",")
    else:
        parts = list(value)
    return [str(tag).strip() for tag in parts if str(tag).strip()]


def iter_jsonl(path: Path) -> Generator[dict[str, Any], None, None]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                raw = json.loads(text)
            except json.JSONDecodeError as exc:
                raise AppError(
                    f"{path.name} {line_no}번째 줄의 JSON이 깨졌습니다.",
                    "손상된 저장 파일을 복구하거나 백업본을 확인하세요.",
                ) from exc
            if not isinstance(raw, dict):
                raise AppError(f"{path.name} {line_no}번째 줄이 JSON 객체가 아닙니다.")
            yield raw


def iter_jsonl_reverse(path: Path, block_size: int = 8192) -> Generator[dict[str, Any], None, None]:
    """Yield JSONL records from newest line to oldest without loading the whole file."""

    if not path.exists() or path.stat().st_size == 0:
        return

    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        position = handle.tell()
        buffer = b""

        while position > 0:
            read_size = min(block_size, position)
            position -= read_size
            handle.seek(position)
            buffer = handle.read(read_size) + buffer
            lines = buffer.split(b"\n")
            buffer = lines[0]

            for raw_line in reversed(lines[1:]):
                text = raw_line.strip()
                if not text:
                    continue
                try:
                    raw = json.loads(text.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise AppError(f"{path.name}에 손상된 JSONL 행이 있습니다.") from exc
                if not isinstance(raw, dict):
                    raise AppError(f"{path.name}에 JSON 객체가 아닌 행이 있습니다.")
                yield raw

        if buffer.strip():
            try:
                raw = json.loads(buffer.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise AppError(f"{path.name}의 첫 행이 손상되었습니다.") from exc
            if not isinstance(raw, dict):
                raise AppError(f"{path.name}의 첫 행이 JSON 객체가 아닙니다.")
            yield raw


def write_jsonl_atomic(path: Path, records: Iterable[dict[str, Any]]) -> None:
    """Rewrite a JSONL file through a same-directory temporary file + os.replace()."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
