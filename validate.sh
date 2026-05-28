#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

TMP_DIR="tmp"
mkdir -p "$TMP_DIR"

# PYTHONPATH=. python3 scripts/validate_export.py export/teochew.csv export/hokkien.csv
PYTHONPATH=. python3 scripts/validate_export.py --errors-only --output "$TMP_DIR/validate_errors.txt" export/teochew.csv export/hokkien.csv
tail -100 "$TMP_DIR/validate_errors.txt"
