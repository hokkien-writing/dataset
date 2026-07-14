#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

TMP_DIR="tmp"
mkdir -p "$TMP_DIR"

if [ $# -gt 0 ]; then
    CSV_FILES=("$@")
else
    CSV_FILES=(export/teochew.csv export/hokkien.csv)
fi

PYTHONPATH=. python3 scripts/validate_export.py --errors-only --output "$TMP_DIR/validate_errors.txt" "${CSV_FILES[@]}" || true
tail -100 "$TMP_DIR/validate_errors.txt"

echo ""
echo "=== PUJ Validation ==="
if [ $# -eq 1 ]; then
    CSV_FILE="$1"
    PUJ_OUTPUT="${CSV_FILE%.csv}.error.csv"
else
    PUJ_OUTPUT="$TMP_DIR/puj_errors.csv"
fi
PYTHONPATH=. python3 scripts/validate_export.py --errors-only --puj "$PUJ_OUTPUT" "${CSV_FILES[@]}"
echo "PUJ errors: $(($(wc -l < "$PUJ_OUTPUT") - 1)) rows"
head -20 "$PUJ_OUTPUT"
