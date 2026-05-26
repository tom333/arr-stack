"""Phase 21 — One-shot migration script (CAT-CLEANUP-02).

Reads .planning/phases/20-categories-cleanup-audit/20-AUDIT.md YAML appendix,
executes per-item os.rename + Radarr/Sonarr PUT + qBit setLocation/setCategory
+ Jellyfin /Library/Refresh. Halt-on-first-error; resume by re-running the
same command — state.json skips already-completed items.

Throwaway — NOT packaged in the arrconf image, NOT a Typer subcommand. Run
from the repo root via `uv run python tools/scripts/migrate-categories.py ...`.
Per D-21-TOOL-02, does NOT trigger chart-pin co-bump (script hors arrconf).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Path injection — makes `from arrconf.…` imports resolve when running from repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "arrconf"))

import structlog  # noqa: E402
from ruyaml import YAML  # noqa: E402

from arrconf.client_base import (  # noqa: E402
    JellyfinClient,
    QbittorrentClient,
    RadarrClient,
    SonarrClient,
)
from arrconf.exceptions import (  # noqa: E402
    ApiClientError,
    AuthError,
    NotFoundError,
    ServerError,
)

log = structlog.get_logger()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI args. Halt-on-first-error; resume via state.json re-run."""
    parser = argparse.ArgumentParser(
        prog="migrate-categories.py",
        description=(
            "One-shot Phase 21 migration: reads 20-AUDIT.md YAML appendix, "
            "executes Radarr/Sonarr PUT + qBit setLocation per item, then "
            "batches Refresh + Jellyfin /Library/Refresh. Halt-on-first-error; "
            "re-run the same command to resume (state.json skips completed items)."
        ),
    )
    parser.add_argument(
        "--audit",
        type=Path,
        required=True,
        help="Path to 20-AUDIT.md (YAML appendix parsed from fenced ```yaml block)",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Execute mutations against cluster",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Log actions without calling APIs",
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=Path(".migration-state.json"),
        help="Resume state file (default: .migration-state.json at CWD; gitignored)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="DEBUG log level",
    )
    return parser.parse_args(argv)


def _check_env_vars(targets: set[str]) -> None:
    """Pre-flight: fail fast (exit 2) if any required env var is missing.

    Mirrors arrconf/__main__.py:217-235 — never start cluster mutations before
    validating the credential contract. D-21-FAIL-01 + 21-PATTERNS.md §3.

    Note: this gate only validates that env vars are NON-EMPTY (dummy values
    pass). Actual HTTP authentication is deferred to per-app branches in
    `main()`, which are gated on `not dry_run` so a `--dry-run` invocation
    with dummy creds genuinely makes zero HTTP calls.
    """
    required: list[tuple[str, str]] = []
    if "radarr" in targets:
        required.append(("RADARR_API_KEY", os.environ.get("RADARR_API_KEY", "")))
    if "sonarr" in targets:
        required.append(("SONARR_API_KEY", os.environ.get("SONARR_API_KEY", "")))
    if "qbittorrent" in targets:
        required.append(("QBT_USER", os.environ.get("QBT_USER", "")))
        required.append(("QBT_PASS", os.environ.get("QBT_PASS", "")))
    if "jellyfin" in targets:
        required.append(("JELLYFIN_API_KEY", os.environ.get("JELLYFIN_API_KEY", "")))
    missing = [name for name, value in required if not value.strip()]
    if missing:
        log.error("missing_env_vars", missing=missing)
        sys.exit(2)


def _load_audit_appendix(audit_path: Path) -> dict[str, Any]:
    """Extract and parse the fenced ```yaml block from 20-AUDIT.md.

    Mirrors arrconf.audit.verify_audit:925-943. Exits 2 on missing file,
    missing fenced block, or parse error.
    """
    if not audit_path.exists():
        log.error("audit_missing", path=str(audit_path))
        sys.exit(2)
    text = audit_path.read_text(encoding="utf-8")
    yaml_block = re.search(r"```yaml\n(.*?)\n```", text, re.DOTALL)
    if not yaml_block:
        log.error("audit_missing_yaml_appendix", input=str(audit_path))
        sys.exit(2)
    yaml = YAML(typ="safe")
    try:
        loaded: Any = yaml.load(yaml_block.group(1))
    except Exception as exc:
        log.error("audit_yaml_parse_error", error=str(exc))
        sys.exit(2)
    return loaded or {}


def _load_state(state_path: Path) -> dict[str, Any]:
    """Load resume state from JSON (or seed empty). Exits 2 on corrupt JSON."""
    if not state_path.exists():
        return {"completed": {"radarr": [], "sonarr": [], "qbittorrent": []}}
    try:
        loaded = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        log.error("state_file_corrupt", path=str(state_path), error=str(exc))
        sys.exit(2)
    if not isinstance(loaded, dict):
        log.error("state_file_not_dict", path=str(state_path), type=type(loaded).__name__)
        sys.exit(2)
    return loaded


def _save_state(state: dict[str, Any], state_path: Path) -> None:
    """Atomic write: tempfile in same dir, then os.rename (POSIX atomic)."""
    parent = state_path.parent if str(state_path.parent) else Path(".")
    parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=str(parent),
        prefix=".migration-state.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=True)
        os.rename(tmp, state_path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def _build_tag_label_to_id(client: SonarrClient | RadarrClient) -> dict[str, int]:
    """GET /tag once, build {label: id} lookup. Mirrors __main__.py:74-82."""
    raw_tags: list[dict[str, Any]] = client.get("/tag")
    return {t["label"]: int(t["id"]) for t in raw_tags if "label" in t and "id" in t}


def main(argv: list[str] | None = None) -> int:
    """Entry point — orchestrate audit load + per-app loops + final summary."""
    args = _parse_args(argv)

    import logging

    level = logging.DEBUG if args.verbose else logging.INFO
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(level))

    audit = _load_audit_appendix(args.audit)
    log.info(
        "audit_loaded",
        radarr_count=len(audit.get("radarr", {}).get("movies_to_migrate", [])),
        sonarr_count=len(audit.get("sonarr", {}).get("series_to_migrate", [])),
        qbit_count=len(audit.get("qbittorrent", {}).get("torrents_to_relocate", [])),
    )

    targets = {app for app in ("radarr", "sonarr", "qbittorrent", "jellyfin") if app in audit}
    _check_env_vars(targets)

    state = _load_state(args.state_file)
    state.setdefault("started_at", datetime.now(UTC).isoformat())
    if not args.dry_run:
        _save_state(state, args.state_file)
    log.info(
        "state_loaded",
        completed=state.get("completed", {}),
        started_at=state.get("started_at"),
    )

    # TODO Task 2: build radarr client + _migrate_radarr_items + _batch_refresh_radarr
    # TODO Task 3: build sonarr client + _migrate_sonarr_items + _batch_refresh_sonarr
    # TODO Task 4: build qbit client + _migrate_qbit_torrents
    # TODO Task 5: build jellyfin client + _refresh_jellyfin

    # Silence unused-import warnings while skeleton is incomplete.
    # These are wired up in Tasks 2-5.
    _ = (
        RadarrClient,
        SonarrClient,
        QbittorrentClient,
        JellyfinClient,
        ApiClientError,
        AuthError,
        NotFoundError,
        ServerError,
        _build_tag_label_to_id,
    )

    log.info("migration_skeleton_complete", dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
