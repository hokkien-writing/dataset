#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
failed=0
for f in scripts/tests/test_*.py; do
  echo "=== $f ==="
  PYTHONPATH=. python3 "$f" || failed=$((failed + 1))
done
if [ "$failed" -ne 0 ]; then
  echo "$failed test file(s) failed"
  exit 1
fi
echo "All tests passed!"
