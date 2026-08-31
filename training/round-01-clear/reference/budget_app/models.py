"""가계부에서 사용하는 데이터의 '모양'을 정의합니다.

이 파일은 파일 저장 방법이나 CLI 출력 방법을 다루지 않습니다. 대신 거래(Transaction),
예산(Budget), CSV 가져오기 결과(ImportResult)가 어떤 필드를 가지는지 정의합니다.
이처럼 데이터 구조를 한곳에 모아 두면 다른 모듈이 같은 형식을 공유하기 쉽습니다.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Transaction:
    """수입 또는 지출 한 건을 표현하는 데이터 클래스.

    ``@dataclass``를 사용하면 ``__init__`` 같은 반복 코드를 Python이 자동으로
    만들어 줍니다. ``slots=True``는 미리 선언한 필드만 사용하도록 제한하여
    오타로 엉뚱한 속성을 만드는 실수를 줄이고 메모리 사용도 조금 줄입니다.

    필드 의미
    ---------
    id:
        거래를 구분하는 고유 ID. 예: ``TX-000001``
    type:
        ``income``(수입) 또는 ``expense``(지출)
    date:
        ``YYYY-MM-DD`` 형식 날짜
    amount:
        0보다 큰 정수 금액
    category:
        등록된 카테고리 이름
    memo:
        선택 입력 메모
    tags:
        검색에 사용할 태그 목록
    """

    id: str
    type: str
    date: str
    amount: int
    category: str
    memo: str = ""

    # 리스트 같은 변경 가능한 값을 기본값으로 직접 []라고 쓰면 여러 객체가
    # 같은 리스트를 공유할 수 있습니다. default_factory=list를 사용하면
    # Transaction이 생성될 때마다 새로운 빈 리스트가 만들어집니다.
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Transaction 객체를 JSON 저장에 적합한 dict로 변환합니다."""

        # asdict()는 dataclass의 필드를 {필드명: 값} 형태로 바꿉니다.
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Transaction":
        """JSON에서 읽은 dict를 다시 Transaction 객체로 복원합니다.

        ``@classmethod``이므로 특정 객체(instance)가 아니라 클래스 자체 ``cls``를
        이용해 새 Transaction을 만듭니다. 저장 데이터에서 tags가 문자열로 들어온
        예외적인 경우도 쉼표 기준으로 나누어 리스트 형태로 정규화합니다.
        """

        tags = raw.get("tags", [])
        if isinstance(tags, str):
            # 예: "meal,lunch" -> ["meal", "lunch"]
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]

        # 파일에서 읽은 값의 타입을 명시적으로 맞춰 객체를 생성합니다.
        return cls(
            id=str(raw["id"]),
            type=str(raw["type"]),
            date=str(raw["date"]),
            amount=int(raw["amount"]),
            category=str(raw["category"]),
            memo=str(raw.get("memo", "")),
            tags=list(tags),
        )


@dataclass(slots=True)
class Budget:
    """한 달의 예산을 표현하는 데이터 클래스.

    예: ``Budget(month="2026-08", amount=500000)``
    """

    month: str
    amount: int

    def to_dict(self) -> dict[str, Any]:
        """Budget 객체를 JSONL에 저장할 수 있는 dict로 변환합니다."""

        return asdict(self)


@dataclass(slots=True)
class ImportResult:
    """CSV import 한 번의 처리 결과를 모아 두는 데이터 클래스.

    ``imported``는 정상 저장된 행 수, ``skipped``는 오류로 건너뛴 행 수이며,
    ``errors``에는 건너뛴 행 번호와 원인을 문자열로 기록합니다.
    """

    imported: int = 0
    skipped: int = 0

    # 각 ImportResult 객체가 자신만의 오류 목록을 갖도록 default_factory를 사용합니다.
    errors: list[str] = field(default_factory=list)
