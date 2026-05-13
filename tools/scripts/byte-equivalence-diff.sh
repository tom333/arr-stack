#!/usr/bin/env bash
# tools/scripts/byte-equivalence-diff.sh
# Compare helm template output against ArgoCD baseline YAML files.
# Usage: byte-equivalence-diff.sh [BASELINE_DIR] [RENDERED_FILE]
#   defaults: evidence/pre-cutover-argocd  /tmp/umbrella-render.yaml

set -euo pipefail
BASELINE_DIR="${1:-.planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd}"
RENDERED="${2:-/tmp/umbrella-render.yaml}"

if [[ ! -d "$BASELINE_DIR" ]]; then
  echo "ERROR: baseline directory not found: $BASELINE_DIR" >&2
  exit 2
fi
if [[ ! -f "$RENDERED" ]]; then
  echo "ERROR: rendered manifest not found: $RENDERED" >&2
  exit 2
fi

echo "Comparing $RENDERED against $BASELINE_DIR..."
if diff <(kubectl apply --dry-run=client -f "$RENDERED" 2>&1 | sort) \
        <(kubectl apply --dry-run=client -f "$BASELINE_DIR" 2>&1 | sort); then
  echo "EQUIVALENT (no unexpected diffs)"
  exit 0
else
  echo "DIFF DETECTED -- review above before proceeding with cutover"
  exit 1
fi
