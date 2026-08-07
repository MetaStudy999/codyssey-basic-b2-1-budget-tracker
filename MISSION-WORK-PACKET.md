# B2-1 Mission Work Packet

## 1. Identity

- Mission: `B2-1` — 나만의 용돈 기입장 프로그램 만들기
- Repository: `MetaStudy999/codyssey-basic-b2-1-budget-tracker`
- Work branch: `mission/B2-1`
- Control Tower: `MetaStudy999/codyssey-basic` (READ ONLY)
- Frozen Control Tower baseline: `0d1581b3e82366988f57e1d76da311c028b8e15e`
- Active Wave: `20260808-01`
- Dependency: `NONE`
- Current Gate at freeze: `G1_SOURCE`

## 2. Source Inventory

| Source | State | Use |
|---|---|---|
| `b2-1-mission.pdf` | `UNREADABLE` in current Workcell renderer | Existence confirmed; content is not treated as directly verified evidence |
| `b2-1-mission.md` | `VALID` | Confirmed Mission requirements; document states it preserves the 9-page PDF wording/requirements |
| `b2-1-evaluation.md` | `VALID` | Confirmed evaluation criteria |
| Control Tower starter packet `docs/00-governance/work-packets/b2-1.md` | `VALID` | Starter structure only; revalidated against Mission/Evaluation |
| Control Tower Mission index path named by starter packet | `MISSING` at frozen baseline | Source Gap only; no requirement is inferred from it |

- Source Mode: `FULL_SOURCE`
- Source Confidence: `MEDIUM`
- Source Gaps:
  1. Highest-priority PDF exists but could not be visually rendered in this Workcell.
  2. Starter Packet's representative Mission index path is absent at the frozen baseline.
- Conflict: none observed between the valid Mission Markdown and Evaluation.
- Rule: gaps above must not be converted into new requirements.

## 3. Mission Contract

### Required deliverable

A Python 3.10+ standard-library-only console budget tracker runnable as:

```bash
python -m budget_app <command> [options]
```

### Required functional scope

- `add` — interactive transaction entry; prints generated unique id.
- `list` — newest-first transaction listing with `--limit`; generator-backed file iteration.
- `search` — filter by `--from`, `--to`, `--category`, `--type`, `--q`, `--tag`; newest-first and generator-backed.
- `summary` — monthly income, expense, balance, expense category TOP N; clear no-data output.
- `budget set` — persist monthly budget; `summary` prints usage percentage and over-budget warning.
- `category add/list/remove` — persist categories; prevent removal while transactions use the category.
- `update` — id-based update; this implementation fixes the contract to option-based update.
- `delete --id` — remove by id and handle missing ids.
- `import --from <csv>` / `export --out <csv>` — UTF-8 CSV with header and fixed columns; export requires month or date range.
- Persist at least three files: transactions, categories, budgets.
- Transaction model fields: `id`, `type`, `date`, `amount`, `category`, optional `memo`, optional `tags`.
- Dataclass or equivalent model; at least two classes.
- At least three modules with explained responsibility boundaries.
- At least one decorator for a real cross-cutting concern.
- Type hints on function/data contracts.
- User-facing validation errors without stack traces; errors exit non-zero.
- All commands expose `--help` through argparse.

### Constraints

- Python `>=3.10`.
- Standard library only; no `pip install` dependency.
- Persistent storage format: JSONL selected for application stores.
- CSV is the interchange format for import/export.
- Global `--data-dir` allows store location override.
- No database or web framework.

### Optional / backlog

The Mission bonus items (backup, recurring transactions, enhanced table formatting, additional atomicity beyond required safety) are not required for STOP. Atomic temp-file replacement is nevertheless used where it directly improves required update/delete/import safety.

## 4. Requirement Traceability

| ID | Requirement | Source | Planned evidence |
|---|---|---|---|
| REQ-B2-1-001 | Python CLI entry point and help | Mission §4.1 | CLI tests / README |
| REQ-B2-1-002 | Transaction dataclass fields and validation | Mission §4.2 | model/unit tests |
| REQ-B2-1-003 | 3+ persistent files, JSONL/CSV, initialization | Mission §4.3 | filesystem tests |
| REQ-B2-1-004 | interactive `add` + generated id | Mission §4.4 | subprocess CLI test |
| REQ-B2-1-005 | newest-first generator-backed `list --limit` | Mission §4.5 | unit + integration tests |
| REQ-B2-1-006 | safe option-based `update` / id-based `delete` | Mission §4.6 | integration/error tests |
| REQ-B2-1-007 | generator-backed filtered `search` | Mission §4.7 | integration tests |
| REQ-B2-1-008 | monthly `summary`, TOP N, no-data message | Mission §4.8 | integration tests |
| REQ-B2-1-009 | persistent budget + usage/overrun | Mission §4.9 | integration tests |
| REQ-B2-1-010 | category add/list/remove and in-use guard | Mission §4.10 | integration tests |
| REQ-B2-1-011 | import/export CSV schema, UTF-8, header, filters | Mission §4.11 | CSV round-trip tests |
| REQ-B2-1-012 | decorator used for cross-cutting concern | Mission decorator section | code inspection/test |
| REQ-B2-1-013 | no traceback + non-zero error exit | Mission exception/exit section | subprocess error tests |
| REQ-B2-1-014 | 3+ modules / 2+ classes / type hints | Mission + Evaluation items 2–3 | code inspection/tests |
| REQ-B2-1-015 | README: run, stores, commands, CSV schema | Mission final deliverable | README review |
| REQ-B2-1-016 | storage-format rationale and 100k scaling explanation | Evaluation item 4 | README learning section |
| REQ-B2-1-017 | broken import-row trust policy explanation | Evaluation item 4 | README + tests |

## 5. Evaluation Mapping

- Evaluation 1 — functional and exception handling → REQ 001–013.
- Evaluation 2 — module/class design and safe file update/delete → REQ 006, 014.
- Evaluation 3 — generator/decorator/type hints → REQ 005, 007, 012, 014.
- Evaluation 4 — format choice, 100k bottleneck, broken-row policy → REQ 016–017.
- Final confirmation → automated CLI transcript/tests + persisted evidence files.

## 6. Repository Baseline

Baseline `main` SHA: `ee0688aef46cc4dd13fad40a96d2abf3d51008bf`.

At G1 start the repository contained only:

- `README.md`
- `b2-1-mission.md`
- `b2-1-mission.pdf`
- `b2-1-evaluation.md`

No application code, tests, application data stores, or prior runtime evidence existed.

## 7. Mission-specific TOC

```text
B2-1
├── Source / Evaluation Discovery
├── CLI Contract
├── Model / Validation
├── JSONL Persistence
├── Transactions: add/list/search/update/delete
├── Categories
├── Budgets / Summary
├── CSV Import / Export
├── Generator Streaming
├── Decorator / Type Hints
├── Error Handling / Exit Codes
├── Automated Tests
├── Evidence
├── Learning / Explanation
└── Handoff
```

## 8. Scope / Non-scope

### Scope

Only files required to implement, test, document, evidence, and hand off B2-1 in this repository.

### Non-scope

- Control Tower changes.
- Other Mission repositories.
- Bonus features not needed for the required/evaluation criteria.
- External dependencies, database, web UI, CI expansion.

## 9. Agent Routing

- Orchestrator / Integrator: ChatGPT.
- Primary Builder: current Workcell implementation path (single builder lane).
- Independent Review: one separate review pass focused only on BLOCKER/MAJOR and evaluation failures.
- Specialist: none unless a documented escalation trigger appears.
- Review budget: self-review 1, independent review 1, targeted revalidation 1 if required.

## 10. Test Plan

1. Syntax/import smoke check.
2. Unit tests for model validation and generator repository iteration.
3. CLI integration tests in temporary `--data-dir` directories.
4. Persistence across separate process invocations.
5. Category in-use removal error path.
6. Budget usage and overrun output.
7. CSV UTF-8/header/schema export and import round-trip.
8. Malformed CSV policy: reject before commit, report user-facing error, preserve existing data.
9. Missing id / invalid date / invalid amount / file errors: no traceback, exit non-zero.
10. `python -m unittest discover -s tests -v` as the required harness command.

## 11. Runtime Plan

All required CLI behavior is executable in an isolated Python environment with the standard library. No OS privilege, cloud account, browser, public URL, or external service is required. Therefore expected G5 state is `NOT-REQUIRED` unless automated execution reveals an environment-only gap.

## 12. Evidence Plan

- `evidence/test-results.txt` — actual automated test output.
- `evidence/cli-transcript.txt` — actual representative CLI flow.
- `evidence/sample-export.csv` — actual exported interchange file.
- README contains reproducible commands and architecture/learning explanations.

## 13. Dependency / Drift Check

- Official/operational dependency for B2-1: `NONE`.
- Active Wave repository/packet mapping matches the launcher.
- Frozen baseline matches the Active Wave.
- `CONTROL_TOWER_DRIFT`: `NONE` for mapping/baseline; missing representative Mission index is recorded as a Source Gap, not silently repaired.

## 14. G1–G8 Checklist

- [x] G1 SOURCE — valid Mission Markdown and Evaluation inspected; inventory, mode, gaps, requirements fixed.
- [ ] G2 BUILD — implement only confirmed scope.
- [ ] G3 TEST — run required automated harness and failure paths.
- [ ] G4 REVIEW — BLOCKER/MAJOR-focused independent review.
- [ ] G5 RUNTIME — automated environment suffices or mark actual exception.
- [ ] G6 EVIDENCE — save only actual outputs.
- [ ] G7 LEARN — explanations grounded in final implementation.
- [ ] G8 MERGE — merge only after required/evaluation/test/evidence + 0 BLOCKER/0 MAJOR.

## 15. STOP Rule

Stop the mission loop when all original required requirements and evaluation requirements are satisfied, required tests pass, runtime is COMPLETE or NOT-REQUIRED, required evidence is complete, and `BLOCKER=0`, `MAJOR=0`. MINOR/style/bonus improvements move to Backlog.

## 16. Handoff Contract

After Mission PR merge, leave `HANDOFF.md` and `mission-result.yaml` in this repository with baseline SHA, final SHA, PR/merge state, Source state/mode/gaps, requirement and gate results, tests, runtime/evidence, learning state, blockers/majors, and backlog. Do not modify the Control Tower from this Workcell.
