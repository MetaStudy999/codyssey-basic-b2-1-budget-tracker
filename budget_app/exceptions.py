class BudgetError(Exception):
    """Expected application error safe to show to CLI users."""

    def __init__(self, message: str, hint: str = "입력값과 파일 경로를 확인해 주세요.") -> None:
        super().__init__(message)
        self.hint = hint
