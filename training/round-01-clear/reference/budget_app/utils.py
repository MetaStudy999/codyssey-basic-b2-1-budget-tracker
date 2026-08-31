"""여러 모듈에서 함께 사용하는 공통 도구를 모아 둔 파일입니다.

주요 역할
---------
1. CLI 공통 오류 처리 데코레이터
2. 날짜/월/type/양수 금액 검증
3. 태그 문자열 정리
4. JSONL 정방향/역방향 스트리밍 읽기
5. 임시 파일 + ``os.replace``를 이용한 원자적(atomic) 재작성

복잡한 기능을 한 곳에 모으는 이유는 같은 검증/파일 처리 코드를 여러 곳에서
중복 작성하지 않기 위해서입니다.
"""

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

# ParamSpec과 TypeVar는 데코레이터가 원래 함수의 인수 형태를 타입 힌트에서
# 최대한 유지하도록 돕습니다. 입문 단계에서는 '함수 타입을 보존하는 도구'로 이해하면 됩니다.
P = ParamSpec("P")
R = TypeVar("R")

# 정규표현식(Regular Expression)으로 날짜/월 문자열의 기본 모양을 먼저 검사합니다.
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def handle_cli_errors(func: Callable[P, int]) -> Callable[P, int]:
    """CLI 함수의 예외를 사용자 친화적 메시지와 종료 코드로 바꾸는 데코레이터.

    ``@handle_cli_errors``를 ``main()`` 위에 붙이면 main 내부에서 발생한 AppError를
    한곳에서 처리할 수 있습니다. 각 command마다 try/except를 반복하지 않아도 되는
    것이 데코레이터를 사용하는 핵심 이유입니다.
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> int:
        try:
            # 정상일 때는 원래 함수의 반환값(대개 exit code 0)을 그대로 돌려줍니다.
            return func(*args, **kwargs)

        except AppError as exc:
            # 우리가 예상하고 설계한 사용자 입력/업무 규칙 오류입니다.
            print(f"[오류] {exc.message}", file=sys.stderr)
            print(f"[힌트] {exc.hint}", file=sys.stderr)
            return 2

        except (OSError, ValueError, json.JSONDecodeError) as exc:
            # 파일 I/O, 값 변환, JSON 파싱처럼 실행 중 충분히 발생할 수 있는 오류입니다.
            print(f"[오류] {exc}", file=sys.stderr)
            print("[힌트] 입력값, 파일 경로와 저장 데이터 형식을 확인해 주세요.", file=sys.stderr)
            return 2

        except Exception as exc:  # Mission rule: no traceback to the user.
            # 예상하지 못한 예외도 Python Traceback 전체를 사용자에게 노출하지 않습니다.
            # 실제 서비스라면 별도의 내부 로그에 상세 Traceback을 남기는 방식을 고려할 수 있습니다.
            print(f"[오류] 처리 중 예상하지 못한 문제가 발생했습니다: {exc}", file=sys.stderr)
            print("[힌트] 입력값과 데이터 파일 상태를 확인한 뒤 다시 실행해 주세요.", file=sys.stderr)
            return 2

    return wrapper


def validate_date(value: str) -> str:
    """문자열이 실제 존재하는 ``YYYY-MM-DD`` 날짜인지 검증합니다."""

    # 1단계: 글자 모양이 4자리-2자리-2자리인지 검사합니다.
    if not DATE_RE.match(value):
        raise AppError("날짜 형식이 올바르지 않습니다.", "YYYY-MM-DD 형식으로 입력하세요. 예: 2026-08-16")

    # 2단계: 2026-99-99처럼 모양은 맞지만 실제 달력에 없는 날짜를 검사합니다.
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise AppError("존재하지 않는 날짜입니다.", "실제 달력에 존재하는 YYYY-MM-DD 날짜를 입력하세요.") from exc

    return value


def validate_month(value: str) -> str:
    """문자열이 실제 존재하는 ``YYYY-MM`` 월인지 검증합니다."""

    if not MONTH_RE.match(value):
        raise AppError("월 형식이 올바르지 않습니다.", "YYYY-MM 형식으로 입력하세요. 예: 2026-08")

    try:
        datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise AppError("존재하지 않는 월입니다.", "01~12 범위의 월을 입력하세요.") from exc

    return value


def positive_int(value: str | int, field_name: str = "금액") -> int:
    """문자열/정수 입력을 0보다 큰 정수로 변환합니다."""

    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise AppError(f"{field_name}은 정수여야 합니다.", "0보다 큰 정수를 입력하세요.") from exc

    if number <= 0:
        raise AppError(f"{field_name}은 0보다 커야 합니다.", "양의 정수를 입력하세요.")

    return number


def validate_type(value: str) -> str:
    """거래 종류를 ``income`` 또는 ``expense``로 제한합니다."""

    # 사용자가 INCOME처럼 대문자로 입력해도 비교할 수 있도록 소문자로 바꿉니다.
    normalized = value.strip().lower()
    if normalized not in {"income", "expense"}:
        raise AppError("type은 income 또는 expense여야 합니다.", "income 또는 expense 중 하나를 입력하세요.")
    return normalized


def parse_tags(value: str | Iterable[str] | None) -> list[str]:
    """태그 입력을 공백 없는 문자열 리스트로 정리합니다.

    예:
    ``"meal, lunch"`` -> ``["meal", "lunch"]``
    """

    if value is None:
        return []

    if isinstance(value, str):
        parts = value.split(",")
    else:
        # 이미 list/tuple 같은 반복 가능한 값이면 list로 복사합니다.
        parts = list(value)

    # 빈 문자열은 버리고 각 태그의 앞뒤 공백을 제거합니다.
    return [str(tag).strip() for tag in parts if str(tag).strip()]


def iter_jsonl(path: Path) -> Generator[dict[str, Any], None, None]:
    """JSONL 파일을 첫 줄부터 한 줄씩 읽어 dict를 yield합니다.

    JSONL(JSON Lines)은 한 줄에 JSON 객체 하나를 저장합니다. 따라서 파일 전체를
    한 번에 ``json.load()``할 필요 없이 한 줄씩 스트리밍할 수 있습니다.
    """

    if not path.exists():
        return

    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            text = line.strip()

            # 빈 줄은 데이터가 아니므로 건너뜁니다.
            if not text:
                continue

            try:
                raw = json.loads(text)
            except json.JSONDecodeError as exc:
                # 어느 파일의 몇 번째 줄이 문제인지 알려 주면 복구하기 쉽습니다.
                raise AppError(
                    f"{path.name} {line_no}번째 줄의 JSON이 깨졌습니다.",
                    "손상된 저장 파일을 복구하거나 백업본을 확인하세요.",
                ) from exc

            # 이 프로그램의 JSONL 한 줄은 항상 { ... } 형태의 JSON 객체여야 합니다.
            if not isinstance(raw, dict):
                raise AppError(f"{path.name} {line_no}번째 줄이 JSON 객체가 아닙니다.")

            yield raw


def iter_jsonl_reverse(path: Path, block_size: int = 8192) -> Generator[dict[str, Any], None, None]:
    """파일 전체를 메모리에 올리지 않고 JSONL을 최신 줄부터 역순으로 읽습니다.

    일반적인 ``readlines()`` 후 ``reversed()``는 파일 전체를 메모리에 올립니다.
    여기서는 파일 끝에서 ``block_size`` 바이트씩 거꾸로 읽어 최신 거래부터
    하나씩 yield합니다. 그래서 ``list --limit 1``처럼 적은 결과만 필요할 때
    전체 파일을 모두 읽지 않고 멈출 수 있습니다.
    """

    if not path.exists() or path.stat().st_size == 0:
        return

    # 텍스트가 아니라 바이너리(rb)로 여는 이유는 파일 끝에서 정확한 byte 위치로
    # seek하기 쉽게 하기 위해서입니다.
    with path.open("rb") as handle:
        # 파일 포인터를 맨 끝으로 이동합니다.
        handle.seek(0, os.SEEK_END)
        position = handle.tell()

        # 블록 경계에서 한 줄이 둘로 잘릴 수 있으므로 남은 조각을 buffer에 보관합니다.
        buffer = b""

        while position > 0:
            # 파일 앞부분에 가까워져 남은 크기가 block_size보다 작으면 남은 만큼만 읽습니다.
            read_size = min(block_size, position)
            position -= read_size
            handle.seek(position)

            # 새로 읽은 앞쪽 블록 + 이전에 남은 뒤쪽 조각을 연결합니다.
            buffer = handle.read(read_size) + buffer
            lines = buffer.split(b"\n")

            # 첫 조각은 앞 블록과 이어질 수 있으므로 다음 반복까지 보관합니다.
            buffer = lines[0]

            # 나머지 완성된 줄은 뒤에서부터 읽어 최신순으로 처리합니다.
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

        # 반복이 끝난 뒤 buffer에 파일의 첫 줄이 남아 있으면 마지막으로 처리합니다.
        if buffer.strip():
            try:
                raw = json.loads(buffer.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise AppError(f"{path.name}의 첫 행이 손상되었습니다.") from exc

            if not isinstance(raw, dict):
                raise AppError(f"{path.name}의 첫 행이 JSON 객체가 아닙니다.")

            yield raw


def write_jsonl_atomic(path: Path, records: Iterable[dict[str, Any]]) -> None:
    """JSONL을 임시 파일에 완성한 뒤 원본과 원자적으로 교체합니다.

    안전한 재작성 순서
    ------------------
    1. 원본과 같은 디렉터리에 임시 파일 생성
    2. 새 내용을 임시 파일에 모두 작성
    3. ``flush()``로 Python 버퍼를 비움
    4. ``os.fsync()``로 운영체제에 디스크 기록을 요청
    5. ``os.replace()``로 임시 파일을 원본 경로에 교체

    기존 파일을 먼저 비우고 쓰는 것보다 중간 실패 시 원본을 보존할 가능성이 높습니다.
    """

    path.parent.mkdir(parents=True, exist_ok=True)

    # 같은 디렉터리에 만들면 최종 os.replace가 같은 파일시스템 안에서 수행됩니다.
    # PID(Process ID)를 붙여 동시에 실행되는 프로세스의 임시 파일 이름 충돌을 줄입니다.
    temp_path = path.with_name(f".{path.name}.tmp-{os.getpid()}")

    try:
        with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")

            # Python 사용자 공간의 버퍼를 운영체제 쪽으로 전달합니다.
            handle.flush()
            # 운영체제에 실제 저장장치 동기화를 요청합니다.
            os.fsync(handle.fileno())

        # 임시 파일 작성이 완전히 끝난 후에만 원본 경로로 교체합니다.
        os.replace(temp_path, path)

    finally:
        # 교체 전에 오류가 발생했을 경우 남아 있을 수 있는 임시 파일을 정리합니다.
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
