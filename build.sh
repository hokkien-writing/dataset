#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python3 scripts/export.py
python3 scripts/export_csv.py
python3 scripts/merge_csv.py
python3 scripts/export_rime.py
