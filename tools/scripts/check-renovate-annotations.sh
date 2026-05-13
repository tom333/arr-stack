#!/usr/bin/env bash
# tools/scripts/check-renovate-annotations.sh
# Verify every 'repository:' line in values.yaml has a renovate annotation above it.
# Usage: check-renovate-annotations.sh [path/to/values.yaml]
#   default: charts/arr-stack/values.yaml

set -euo pipefail
VALUES="${1:-charts/arr-stack/values.yaml}"
ERRORS=0
prev=""

if [[ ! -f "$VALUES" ]]; then
  echo "ERROR: file not found: $VALUES" >&2
  exit 2
fi

while IFS= read -r line; do
  if [[ "$line" =~ ^[[:space:]]*repository: ]]; then
    if [[ ! "$prev" =~ renovate:.*image= ]]; then
      echo "MISSING renovate annotation before: $line"
      ERRORS=$((ERRORS + 1))
    fi
  fi
  prev="$line"
done < "$VALUES"

if [[ $ERRORS -gt 0 ]]; then
  echo "ERROR: $ERRORS missing renovate annotations"
  exit 1
fi
echo "OK: all repository: lines have renovate annotations"
