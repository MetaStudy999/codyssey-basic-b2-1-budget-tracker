"""사용자에게 보여 줄 '예상 가능한 오류'를 정의합니다.

프로그램 내부에서 발생하는 모든 예외(Exception)를 그대로 터미널에 보여 주면
입문자는 긴 Traceback 때문에 실제 원인을 찾기 어렵습니다. B2-1 Reference에서는
사용자 입력 오류처럼 예상 가능한 문제를 ``AppError``로 표현하고, ``utils.py``의
``handle_cli_errors`` 데코레이터가 이를 친절한 메시지로 바꿔 출력합니다.
"""


class AppError(Exception):
    """사용자에게 원인과 해결 힌트를 보여 주기 위한 애플리케이션 오류.

    Parameters
    ----------
    message:
        무엇이 잘못되었는지 설명하는 핵심 오류 메시지입니다.
    hint:
        사용자가 다음에 무엇을 확인하거나 고쳐야 하는지 알려 주는 안내입니다.

    예를 들어 금액이 0이면 ``message``에는 "금액은 0보다 커야 합니다."를,
    ``hint``에는 "양의 정수를 입력하세요."를 넣을 수 있습니다.
    """

    def __init__(self, message: str, hint: str = "입력값과 사용법을 확인해 주세요.") -> None:
        # 부모 Exception에도 message를 전달해 Python 예외의 기본 동작을 유지합니다.
        super().__init__(message)

        # 아래 두 속성은 CLI 오류 처리 데코레이터에서 각각 [오류], [힌트]로 출력합니다.
        self.message = message
        self.hint = hint
