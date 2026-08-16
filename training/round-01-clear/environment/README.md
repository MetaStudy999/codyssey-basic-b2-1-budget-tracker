# B2-1 R01 Environment

B2-1은 Python 표준 라이브러리만 사용하므로 별도 `setup.sh`나 `requirements.txt`가 필요하지 않습니다.

## Golden Path

- Python 3.10+
- Linux/macOS/WSL2/Windows에서 Python CLI 실행 가능
- 외부 pip 패키지 없음
- Repository 루트에서 `PYTHONPATH`로 Reference package를 지정

```bash
python3 --version
export PYTHONPATH="$PWD/training/round-01-clear/reference"
python -m budget_app --help
```

Windows PowerShell에서는:

```powershell
$env:PYTHONPATH="$PWD\training\round-01-clear\reference"
python -m budget_app --help
```

## 역할

- `verify.sh`: Reference 코드 문법·테스트·핵심 파일을 검증만 합니다.
- `reset.sh`: Runtime 학습 중 생성한 지정 데이터 디렉터리만 명시적 확인 후 제거합니다.

## 저장 데이터

기본 실행은 현재 작업 디렉터리의 `./data`를 사용합니다. 학습 중 기존 개인 데이터를 건드리지 않으려면 별도 디렉터리를 권장합니다.

```bash
python -m budget_app --data-dir /tmp/codyssey-b2-1-data category list
```

## Secret

B2-1 공식 미션에는 API Key/Password가 필요하지 않습니다. 향후 확장 과정에서 실제 Secret을 추가하더라도 Repository에는 저장하지 않습니다.
