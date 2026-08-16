#!/usr/bin/env bash
# B2-1 R01 verification-only helper.
# It validates the Reference implementation without writing mission data into
# the repository. Unit tests use TemporaryDirectory internally.

set -u

PASS=0
FAIL=0
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROUND_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
REFERENCE_DIR="$ROUND_DIR/reference"
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd)
TEST_OUT=$(mktemp /tmp/b2-1-unittest.XXXXXX)
trap 'rm -f "$TEST_OUT"' EXIT

pass() { echo "[PASS] $1"; PASS=$((PASS + 1)); }
fail() { echo "[FAIL] $1"; FAIL=$((FAIL + 1)); }

if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
else
    echo "[FAIL] Python not found"
    echo "Result: 0 PASS / 1 FAIL"
    exit 1
fi

VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if $PYTHON -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)'; then
    pass "Python >= 3.10 ($VERSION)"
else
    fail "Python >= 3.10 required ($VERSION)"
fi

REQUIRED_FILES=(
    "$REFERENCE_DIR/budget_app/__init__.py"
    "$REFERENCE_DIR/budget_app/__main__.py"
    "$REFERENCE_DIR/budget_app/models.py"
    "$REFERENCE_DIR/budget_app/repositories.py"
    "$REFERENCE_DIR/budget_app/services.py"
    "$REFERENCE_DIR/budget_app/cli.py"
    "$REFERENCE_DIR/budget_app/utils.py"
    "$REFERENCE_DIR/budget_app/errors.py"
    "$REFERENCE_DIR/tests/test_budget_app.py"
    "$REFERENCE_DIR/README.md"
    "$ROUND_DIR/BEGINNER-GUIDE.md"
    "$ROUND_DIR/CHECKLIST.md"
    "$ROUND_DIR/REFERENCE-BUILD.md"
    "$ROUND_DIR/docs/requirements-mapping.md"
    "$ROUND_DIR/docs/evaluation-qa.md"
    "$ROUND_DIR/evidence/README.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    [ -f "$file" ] \
        && pass "file exists: ${file#$REPO_ROOT/}" \
        || fail "file missing: ${file#$REPO_ROOT/}"
done

# Syntax parse only; unlike compileall this does not create __pycache__ files.
if REFERENCE_DIR="$REFERENCE_DIR" $PYTHON - <<'PY'
import ast
import os
from pathlib import Path

root = Path(os.environ["REFERENCE_DIR"])
for path in sorted(root.rglob("*.py")):
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
PY
then
    pass "Python AST syntax parse"
else
    fail "Python AST syntax parse"
fi

# Structural requirements that are central to the evaluation.
grep -q '@dataclass' "$REFERENCE_DIR/budget_app/models.py" \
    && pass "dataclass model exists" || fail "dataclass model missing"
grep -q 'yield ' "$REFERENCE_DIR/budget_app/repositories.py" \
    && pass "repository generator/yield exists" || fail "repository generator/yield missing"
grep -q 'yield ' "$REFERENCE_DIR/budget_app/services.py" \
    && pass "service streaming/yield exists" || fail "service streaming/yield missing"
grep -q '@handle_cli_errors' "$REFERENCE_DIR/budget_app/cli.py" \
    && pass "error-handling decorator applied" || fail "error-handling decorator not applied"
grep -q 'os.replace' "$REFERENCE_DIR/budget_app/utils.py" \
    && pass "atomic replace implementation exists" || fail "atomic replace implementation missing"

# Run unit tests without leaving bytecode/cache in the repository.
if PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REFERENCE_DIR" \
    $PYTHON -m unittest discover -s "$REFERENCE_DIR/tests" -p 'test_*.py' >"$TEST_OUT" 2>&1; then
    pass "Reference unit tests"
else
    fail "Reference unit tests"
    sed 's/^/       /' "$TEST_OUT"
fi

# Root and every main functional command must expose help.
if PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REFERENCE_DIR" \
    $PYTHON -m budget_app --help >/dev/null 2>&1; then
    pass "root --help works"
else
    fail "root --help failed"
fi

for command in add list search summary update delete budget category import export; do
    if PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REFERENCE_DIR" \
        $PYTHON -m budget_app "$command" --help >/dev/null 2>&1; then
        pass "help works: $command"
    else
        fail "help failed: $command"
    fi
done

# All CLI option spellings in Reference source should use GNU-style -- names.
# argparse's internal positional names are not checked here.
if grep -REn "add_argument\(['\"]-[^-]" "$REFERENCE_DIR/budget_app/cli.py" >/dev/null 2>&1; then
    fail "single-dash long option detected"
else
    pass "CLI long options use -- convention"
fi

# README requirements: execution, persistence location/format, commands and CSV schema.
for token in 'Python 3.10' 'transactions.jsonl' 'categories.jsonl' 'budgets.jsonl' 'CSV import/export 스키마' 'python -m budget_app'; do
    grep -q "$token" "$REFERENCE_DIR/README.md" \
        && pass "Reference README covers: $token" \
        || fail "Reference README missing: $token"
done

# The three persistence files are created by BudgetService; tests also reopen
# them to prove transaction/category/budget durability.
for token in 'transactions.jsonl' 'categories.jsonl' 'budgets.jsonl'; do
    grep -q "$token" "$REFERENCE_DIR/budget_app/repositories.py" \
        && pass "persistent store defined: $token" \
        || fail "persistent store missing: $token"
done

if command -v git >/dev/null 2>&1 && git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    TRACKED=$(git -C "$REPO_ROOT" ls-files 'training/round-01-clear/**' \
        | grep -E '(^|/)(\.env($|\.)|.*\.(key|pem)$|secrets/)' || true)
    [ -z "$TRACKED" ] \
        && pass "no tracked Secret-pattern files" \
        || fail "tracked Secret-pattern files detected"
fi

echo
printf 'Result: %d PASS / %d FAIL\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
