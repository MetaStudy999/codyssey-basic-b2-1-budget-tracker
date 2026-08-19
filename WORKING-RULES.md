# B2-1 작업 룰(Working Rules)

이 문서는 B2-1에서 사용하는 **미션별 작업 운영 어댑터(Mission Working Rules Adapter)**입니다. 공통 규칙 전문을 복제하지 않고 메인 레포(Control Tower)의 상위 표준을 사용합니다.

## 빠른 적용(Quick Apply)

```text
B2-1 공식 Mission / Evaluation / 제공 파일
→ 현재 B2-1 Repository main
→ Control Tower 상위 작업 운영 표준
→ BEGINNER-GUIDE / CHECKLIST
→ 실제 실행(Runtime Execution)
→ 검증(Verification)
→ 증빙 자료(Evidence)
→ 평가(Evaluation)
→ 조건 충족 시에만 B2-1 CLEAR
```

## 📑 목차

- [기준 우선순위](#priority)
- [공통 작업 운영 표준](#standard)
- [B2-1 실행 문서](#local)
- [상태와 실행 규칙](#runtime)
- [변경 관리](#change)

<a id="priority"></a>
## 기준 우선순위

```text
1. B2-1 공식 Mission / Evaluation / 제공 파일
2. 이 Repository의 실제 main
3. Control Tower 실제 main
4. Control Tower standards/
5. B2-1 학습·실행 문서
```

공식 요구사항과 내부 표준이 충돌하면 공식 요구사항이 우선합니다.

<a id="standard"></a>
## 공통 작업 운영 표준

- [Codyssey Working Operating Standard](https://github.com/MetaStudy999/codyssey-basic/blob/main/standards/CODYSSEY-WORKING-OPERATING-STANDARD.md)

세부 용어·모듈화·환경·명령 설명·검증·증빙 규칙도 위 메인 레포 `standards/`를 사용합니다.

<a id="local"></a>
## B2-1 실행 문서

- [`README.md`](README.md) — 미션 진입
- [`training/round-01-clear/BEGINNER-GUIDE.md`](training/round-01-clear/BEGINNER-GUIDE.md) — 전체 중앙 허브(Global Hub)
- [`training/round-01-clear/CHECKLIST.md`](training/round-01-clear/CHECKLIST.md) — 실제 완료 판정
- [`training/round-01-clear/environment/`](training/round-01-clear/environment/) — 실행 환경·검증
- [`training/round-01-clear/evidence/`](training/round-01-clear/evidence/) — 실제 증빙 자료(Evidence)

<a id="runtime"></a>
## 상태와 실행 규칙

```text
Documentation Ready
≠ BEGINNER READY
≠ Runtime PASS
≠ Verification PASS
≠ Evidence Complete
≠ Mission CLEAR
```

실제 Runtime에서는 **Preflight → 한 단계 실행 → 실제 출력 → STOP/GO → 검증 → 다음 단계** 순서를 사용합니다. 실제 결과 없이 PASS/CLEAR를 기록하지 않습니다.

비밀정보(Secret)는 값이 아니라 존재·경로·소유권·그룹·권한 등 메타데이터 중심으로 검증합니다.

<a id="change"></a>
## 변경 관리

```text
최신 main 확인
→ 대상 파일 현재 상태/SHA 확인
→ 최소 변경
→ Commit
→ 실제 GitHub main 재확인
→ APPLY & VERIFY
```

이 문서에는 B2-1 고유 예외만 추가하고, 공통 작업 룰 전문을 복제하지 않습니다.
