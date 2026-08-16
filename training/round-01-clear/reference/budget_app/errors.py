class AppError(Exception):
    """Expected user-facing application error without a traceback."""

    def __init__(self, message: str, hint: str = "입력값과 사용법을 확인해 주세요.") -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
