#!/usr/bin/env bash
# B2-1 R01 verification-only helper.

set -u

PASS=0
FAIL=0
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROUND_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
REFERENCE_DIR="$ROUND_DIR/reference"
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd)

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

for file in \
    "$REFERENCE_DIR/budget_app/__init__.py" \
    "$REFERENCE_DIR/budget_app/__main__.py" \
    "$REFERENCE_DIR/budget_app/models.py" \
    "$REFERENCE_DIR/budget_app/repositories.py" \
    "$REFERENCE_DIR/budget_app/services.py" \
    "$REFERENCE_DIR/budget_app/cli.py" \
    "$REFERENCE_DIR/budget_app/utils.py" \
    "$REFERENCE_DIR/budget_app/errors.py" \
    "$REFERENCE_DIR/tests/test_budget_app.py" \
    "$REFERENCE_DIR/README.md"; do
    [ -f "$file" ] && pass "file exists: ${file#$REPO_ROOT/}" || fail "file missing: ${file#$REPO_ROOT/}"
done

if PYTHONPATH="$REFERENCE_DIR" $PYTHON -m compileall -q "$REFERENCE_DIR/budget_app"; then
    pass "Python syntax compile"
else
    fail "Python syntax compile"
fi

if PYTHONPATH="$REFERENCE_DIR" $PYTHON -m unittest discover -s "$REFERENCE_DIR/tests" -p 'test_*.py' >/tmp/b2-1-unittest.out 2>&1; then
    pass "Reference unit tests"
else
    fail "Reference unit tests (see /tmp/b2-1-unittest.out)"
fi

for command in add list search summary update delete budget category import export; do
    if PYTHONPATH="$REFERENCE_DIR" $PYTHON -m budget_app "$command" --help >/dev/null 2>&1; then
        pass "help works: $command"
    else
        fail "help failed: $command"
    fi
done

if command -v git >/dev/null 2>&1 && git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    TRACKED=$(git -C "$REPO_ROOT" ls-files 'training/round-01-clear/**' | grep -E '(^|/)(\.env($|\.)|.*\.(key|pem)$|secrets/)' || true)
    [ -z "$TRACKED" ] && pass "no tracked Secret-pattern files" || fail "tracked Secret-pattern files detected"
fi

echo
printf 'Result: %d PASS / %d FAIL\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
