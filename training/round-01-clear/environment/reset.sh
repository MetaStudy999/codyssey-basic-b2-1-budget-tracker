#!/usr/bin/env bash
# Remove only an explicitly named B2-1 practice data directory.

set -euo pipefail

TARGET="${1:-}"
CONFIRM="${2:-}"

if [ -z "$TARGET" ] || [ "$CONFIRM" != "--apply" ]; then
    cat <<'EOF'
Usage:
  ./reset.sh <practice-data-dir> --apply

Safety rules:
- refuses empty path, /, and HOME
- removes only the explicitly supplied practice data directory
- never removes repository source files
EOF
    exit 0
fi

TARGET_REAL=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$TARGET")
HOME_REAL=$(python3 -c 'import os; print(os.path.realpath(os.path.expanduser("~")))')

if [ "$TARGET_REAL" = "/" ] || [ "$TARGET_REAL" = "$HOME_REAL" ] || [ -z "$TARGET_REAL" ]; then
    echo "[FAIL] unsafe reset target: $TARGET_REAL" >&2
    exit 1
fi

if [ ! -d "$TARGET_REAL" ]; then
    echo "[INFO] target does not exist: $TARGET_REAL"
    exit 0
fi

rm -rf -- "$TARGET_REAL"
echo "[PASS] removed practice data directory: $TARGET_REAL"
