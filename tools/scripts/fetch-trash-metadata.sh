#!/usr/bin/env bash
# tools/scripts/fetch-trash-metadata.sh
# Fetch TRaSH-Guides CF/QP + Recyclarr config-templates at pinned SHAs
# and write baked static assets under tools/arrconf-ui/web/src/assets/trash-metadata/.
# Usage: ./tools/scripts/fetch-trash-metadata.sh [--dry-run]
#
# Environment overrides (optional — defaults are the pinned SHAs from Phase 27):
#   TRASH_SHA       — 40-char SHA for TRaSH-Guides/Guides
#   RECYCLARR_SHA   — 40-char SHA for recyclarr/config-templates
#
# Exit codes: 0=success, 1=transform/validation failure, 2=missing tool/bad SHA fetch

set -euo pipefail

# ── Tool guards ────────────────────────────────────────────────────────────────
command -v curl    >/dev/null || { echo "ERROR: curl required" >&2; exit 2; }
command -v python3 >/dev/null || { echo "ERROR: python3 required" >&2; exit 2; }

# ── Pinned SHAs ────────────────────────────────────────────────────────────────
TRASH_SHA="${TRASH_SHA:-1ef7baa523a5f6585a987a4dab6e06bc96994a74}"
RECYCLARR_SHA="${RECYCLARR_SHA:-505c1e565c08d994520c0ca46fc23dee7bf99fd9}"

# ── Flags ──────────────────────────────────────────────────────────────────────
DRY_RUN=false
for arg in "$@"; do
  [[ "$arg" == "--dry-run" ]] && DRY_RUN=true
done

# ── Output directory ───────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUT_DIR="$REPO_ROOT/tools/arrconf-ui/web/src/assets/trash-metadata"

if $DRY_RUN; then
  echo "DRY-RUN: would fetch TRaSH SHA=$TRASH_SHA, Recyclarr SHA=$RECYCLARR_SHA"
  echo "DRY-RUN: would write 7 files + manifest to $OUT_DIR"
  exit 0
fi

mkdir -p "$OUT_DIR"

echo "Fetching TRaSH-Guides file tree (SHA=$TRASH_SHA)..."
TREE_JSON=$(curl --fail --silent \
  "https://api.github.com/repos/TRaSH-Guides/Guides/git/trees/${TRASH_SHA}?recursive=1") \
  || { echo "ERROR: failed to fetch TRaSH-Guides git tree (HTTP error)" >&2; exit 2; }

echo "Fetching Recyclarr includes.json (SHA=$RECYCLARR_SHA)..."
RECYCLARR_JSON=$(curl --fail --silent \
  "https://raw.githubusercontent.com/recyclarr/config-templates/${RECYCLARR_SHA}/includes.json") \
  || { echo "ERROR: failed to fetch Recyclarr includes.json (HTTP error)" >&2; exit 2; }

echo "Transforming and writing catalog files..."

export TRASH_SHA RECYCLARR_SHA OUT_DIR

python3 - <<'PY'
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

TRASH_SHA     = os.environ["TRASH_SHA"]
RECYCLARR_SHA = os.environ["RECYCLARR_SHA"]
out_dir       = os.environ["OUT_DIR"]
os.makedirs(out_dir, exist_ok=True)

# ── Read the shell-fetched data via stdin is not possible here; re-fetch via urllib ──
def fetch_url(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "fetch-trash-metadata/1.0"})
    with urllib.request.urlopen(req) as resp:
        if resp.status != 200:
            print(f"ERROR: HTTP {resp.status} for {url}", file=sys.stderr)
            sys.exit(2)
        return resp.read()

# ── Fetch TRaSH-Guides git tree ────────────────────────────────────────────────
print("  Fetching TRaSH-Guides git tree...", flush=True)
tree_url = f"https://api.github.com/repos/TRaSH-Guides/Guides/git/trees/{TRASH_SHA}?recursive=1"
tree_data = json.loads(fetch_url(tree_url))
if tree_data.get("truncated"):
    print("WARNING: git tree was truncated — some files may be missing", file=sys.stderr)

all_paths = [item["path"] for item in tree_data.get("tree", []) if item["type"] == "blob"]

def raw_url(path: str) -> str:
    return f"https://raw.githubusercontent.com/TRaSH-Guides/Guides/{TRASH_SHA}/{path}"

# ── Custom Formats ─────────────────────────────────────────────────────────────
def fetch_cf_catalog(app: str) -> list[dict]:
    prefix = f"docs/json/{app}/cf/"
    paths  = [p for p in all_paths if p.startswith(prefix) and p.endswith(".json")]
    print(f"  Fetching {len(paths)} {app} CF files...", flush=True)
    entries = []
    for path in paths:
        raw = json.loads(fetch_url(raw_url(path)))
        entries.append({
            "trash_id":      raw["trash_id"],
            "name":          raw["name"],
            "default_score": raw.get("trash_scores", {}).get("default", 0),
        })
    entries.sort(key=lambda e: e["name"].casefold())
    return entries

sonarr_cf = fetch_cf_catalog("sonarr")
radarr_cf = fetch_cf_catalog("radarr")

# ── Quality Profiles ───────────────────────────────────────────────────────────
def fetch_qp_catalog(app: str) -> list[dict]:
    prefix = f"docs/json/{app}/quality-profiles/"
    paths  = [p for p in all_paths if p.startswith(prefix) and p.endswith(".json")]
    print(f"  Fetching {len(paths)} {app} QP files...", flush=True)
    entries = []
    for path in paths:
        raw = json.loads(fetch_url(raw_url(path)))
        entry: dict = {
            "trash_id":        raw["trash_id"],
            "name":            raw["name"],
            "trash_description": raw.get("trash_description", ""),
            "upgradeAllowed":  raw.get("upgradeAllowed", False),
            "cutoff":          raw.get("cutoff", ""),
            "minFormatScore":  raw.get("minFormatScore", 0),
            "cutoffFormatScore": raw.get("cutoffFormatScore", 10000),
            "items":           raw.get("items", []),
        }
        if "trash_score_set" in raw:
            entry["trash_score_set"] = raw["trash_score_set"]
        if "language" in raw:
            entry["language"] = raw["language"]
        entries.append(entry)
    entries.sort(key=lambda e: e["name"].casefold())
    return entries

sonarr_qp = fetch_qp_catalog("sonarr")
radarr_qp = fetch_qp_catalog("radarr")

# ── Recyclarr includes.json ────────────────────────────────────────────────────
print("  Fetching Recyclarr includes.json...", flush=True)
recyclarr_url  = f"https://raw.githubusercontent.com/recyclarr/config-templates/{RECYCLARR_SHA}/includes.json"
recyclarr_data = json.loads(fetch_url(recyclarr_url))

recyclarr_sonarr = recyclarr_data.get("sonarr", [])
recyclarr_radarr = recyclarr_data.get("radarr", [])

# ── Write catalog files ────────────────────────────────────────────────────────
def write_json(filename: str, data: object) -> None:
    path = os.path.join(out_dir, filename)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=False)
        fh.write("\n")
    print(f"  Wrote {filename} ({len(data) if isinstance(data, list) else 'object'} entries)")  # type: ignore[arg-type]

write_json("sonarr-cf.json",          sonarr_cf)
write_json("radarr-cf.json",          radarr_cf)
write_json("sonarr-qp.json",          sonarr_qp)
write_json("radarr-qp.json",          radarr_qp)
write_json("recyclarr-sonarr.json",   recyclarr_sonarr)
write_json("recyclarr-radarr.json",   recyclarr_radarr)

# ── Write manifest ─────────────────────────────────────────────────────────────
manifest = {
    "trash_sha":      TRASH_SHA,
    "recyclarr_sha":  RECYCLARR_SHA,
    "fetched_at":     datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "counts": {
        "sonarr_cf":          len(sonarr_cf),
        "radarr_cf":          len(radarr_cf),
        "sonarr_qp":          len(sonarr_qp),
        "radarr_qp":          len(radarr_qp),
        "sonarr_recyclarr":   len(recyclarr_sonarr),
        "radarr_recyclarr":   len(recyclarr_radarr),
    },
}
write_json("manifest.json", manifest)

print(f"\nCounts: sonarr_cf={len(sonarr_cf)}, radarr_cf={len(radarr_cf)}, "
      f"sonarr_qp={len(sonarr_qp)}, radarr_qp={len(radarr_qp)}, "
      f"sonarr_recyclarr={len(recyclarr_sonarr)}, radarr_recyclarr={len(recyclarr_radarr)}")
print("Done.")
PY
