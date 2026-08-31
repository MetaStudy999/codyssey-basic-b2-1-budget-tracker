"""``python -m budget_app`` 실행을 시작하는 파일.

Python에서 ``python -m 패키지이름``을 실행하면 그 패키지의 ``__main__.py``가
실행됩니다. 따라서 B2-1에서 권장하는 명령인 ``python -m budget_app``은
이 파일을 거쳐 ``cli.py``의 ``main()`` 함수로 연결됩니다.
"""

# 실제 CLI(Command Line Interface, 명령줄 인터페이스) 로직은 cli.py에 둡니다.
# 이렇게 역할을 나누면 __main__.py는 '실행 시작점'이라는 한 가지 책임만 가집니다.
from .cli import main


if __name__ == "__main__":
    # main()은 성공 시 0, 오류 시 0이 아닌 종료 코드(exit code)를 반환합니다.
    # SystemExit에 그 값을 전달하면 터미널/쉘도 프로그램 성공·실패를 판단할 수 있습니다.
    raise SystemExit(main())
