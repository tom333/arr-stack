# Phase 21: Filesystem + metadata migration — Pattern Map

**Mapped:** 2026-05-26
**Files analyzed:** 4 new artefacts (1 Python script, 1 runbook, 1 state file, 1 snapshot dir pair)
**Analogs found:** 3 / 4 (snapshot dirs = pure outputs of an existing tool, no analog needed)

---

## File Classification

| New file | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `tools/scripts/migrate-categories.py` | script (one-shot CLI) | batch + request-response (API mutations per item) | `tools/arrconf/arrconf/audit.py` (peer YAML-consumer/emitter in same project) + `tools/arrconf/arrconf/__main__.py` (CLI shape) | role-match (peer, not exact — audit is read-only, migrate is mutating) |
| `.planning/phases/21-filesystem-metadata-migration/21-RUNBOOK.md` | runbook (operator narrative) | n/a (documentation) | `CLAUDE.md §"Filesystem migration: v0.2.0 flat → v0.3.0 Categories"` (lines 518-605) | exact (same kind of narrative — pre-check / execution / post-check / rollback) |
| `.migration-state.json` (or `--state-file PATH`) | state file (runtime resume) | file-I/O (atomic write) | no project analog (arrconf is stateless) — see RESEARCH-less guidance from CONTEXT §"State persistance via JSON" | no analog (new pattern) |
| `snapshots/before-categories-cleanup-YYYY-MM-DD/` + `…/after-…` | snapshot artefact | output of existing tool | `snapshots/before-phase-16-2026-05-24/` etc. (output of `tools/snapshot/snapshot.sh`) | exact (zero new code — invoke existing tool) |

**Deltas vs Phase 20 (the closest peer):**
- Phase 20 script lives in `tools/arrconf/` (package) + bumps `arrconf.image.tag` (co-bump rule). Phase 21 lives in **`tools/scripts/`** + **does NOT bump** the chart tag (D-21-TOOL-02).
- Phase 20 script is read-only (`grep -E '\.(post|put|delete|post_form)\('` returns 0). Phase 21 script **must** call PUT/POST — the read-only invariant is reversed.
- Phase 20 has full respx test suite (≥15 tests, 70% gate). Phase 21 **has no test obligation** (D-21-TOOL-03 — throwaway). Triade Python (ruff format / ruff check) optional for lisibilité.
- Phase 20 invocation: `uv run arrconf audit ...` (Typer subcommand in package). Phase 21 invocation: `uv run python tools/scripts/migrate-categories.py ...` (standalone `__main__`).

---

## Pattern Assignments

### `tools/scripts/migrate-categories.py` (script, batch + request-response)

**Analog A:** `tools/arrconf/arrconf/audit.py` (peer YAML-consumer/emitter, same Phase 20-21 axis)
**Analog B:** `tools/arrconf/arrconf/__main__.py` (CLI shape — argparse-or-Typer + env gates + exit-code contract)
**Analog C:** `tools/arrconf/arrconf/reconcilers/qbittorrent.py` (POST/PUT against cluster — the mutating side)
**Analog D:** `tools/arrconf/arrconf/client_base.py` (the HTTP clients to import via path-injection per CONTEXT §"Reusable Assets")

The script is the **inverse** of `audit.py`: audit produces the YAML appendix, migrate **consumes** the same YAML appendix and executes the mutations it prescribes.

---

#### 1. Module header + imports — path-injection pattern (NEW for this script)

Because the script lives in `tools/scripts/` (NOT in `tools/arrconf/`), it cannot `from arrconf.client_base import …` directly without `sys.path` manipulation OR running from `tools/arrconf/` via `uv run python ../scripts/migrate-categories.py`. Two options:

**Option 1 (recommended — explicit, no install):**
```python
"""Phase 21 — One-shot migration script.

Reads .planning/phases/20-categories-cleanup-audit/20-AUDIT.md YAML appendix,
executes Radarr/Sonarr API PUT + qBit setLocation/setCategory + Jellyfin
/Library/Refresh per item. Halt-on-first-error; resume via state.json.

Throwaway — NOT packaged in arrconf image, NOT a Typer subcommand. Run from
the repo root via `uv run python tools/scripts/migrate-categories.py ...`.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

# Path injection: make `from arrconf.…` imports resolve when running from repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "arrconf"))

import structlog
from ruyaml import YAML

from arrconf.client_base import (  # type: ignore[import-not-found]
    JellyfinClient,
    QbittorrentClient,
    RadarrClient,
    SonarrClient,
)
from arrconf.exceptions import ApiClientError, AuthError, ServerError  # type: ignore[import-not-found]

log = structlog.get_logger()
```

**Why path-injection over a venv install:** the script is throwaway; we don't want to publish it as an arrconf entrypoint. Path-injection keeps the script self-contained while reusing the battle-tested `ArrApiClient` (retry, 401/404 classification, qBit cookie auth, Jellyfin MediaBrowser header).

---

#### 2. CLI flags — argparse (simpler than Typer for 5 flags)

**Analog:** `tools/snapshot/snapshot.sh` (lines 62-85) — bash argparse for the same kind of one-shot tool. Same shape, but in Python:

```python
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="migrate-categories.py",
        description=(
            "One-shot Phase 21 migration: reads 20-AUDIT.md YAML appendix, "
            "executes Radarr/Sonarr API mutations + qBit setLocation per item, "
            "then batches Refresh + Jellyfin /Library/Refresh."
        ),
    )
    parser.add_argument(
        "--audit",
        type=Path,
        required=True,
        help="Path to 20-AUDIT.md (the YAML appendix is parsed from the fenced ```yaml block)",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--apply", action="store_true", help="Execute mutations against cluster")
    group.add_argument("--dry-run", action="store_true", help="Log actions without calling APIs")
    parser.add_argument(
        "--state-file",
        type=Path,
        default=Path(".migration-state.json"),
        help="Resume state file (default: .migration-state.json at CWD; gitignored)",
    )
    parser.add_argument(
        "--resume-from",
        type=str,
        default=None,
        help="Force-resume from a specific item id (overrides state.json completed list)",
    )
    parser.add_argument("--verbose", action="store_true", help="DEBUG log level")
    return parser.parse_args(argv)
```

**Why argparse not Typer:** D-21-TOOL-03 says "argparse simple — pas besoin de Typer pour 4 flags" (CONTEXT §"Established Patterns"). Typer is the package CLI framework; this is a script.

**Exit code contract** — mirror `arrconf/__main__.py` (line 1-8):
- `0` — success (or dry-run completed without error)
- `1` — runtime failure (API 4xx/5xx, filesystem mv error)
- `2` — config error (missing audit file, missing env var, malformed YAML appendix)

---

#### 3. Pre-flight gates — env-var fail-fast

**Analog:** `tools/arrconf/arrconf/__main__.py` lines 217-235 (qBit pre-flight) + 245-247 (per-app missing-api-key gate). Verbatim shape:

```python
def _check_env_vars(targets: set[str]) -> None:
    """Pre-flight: fail fast (exit 2) if any required env var is missing.

    Mirrors arrconf/__main__.py:217-235 — never start cluster mutations
    before validating the credential contract.
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
```

**Note — same env names as arrconf** (so the operator can reuse the `arrconf-env` sealed-secret extraction pattern from Phase 20 Task 6 verbatim). See CONTEXT §"Integration Points" for the extraction recipe.

---

#### 4. YAML appendix parsing — regex + ruyaml

**Analog:** `tools/arrconf/arrconf/audit.py` lines 925-943 (`verify_audit` function). Verbatim:

```python
import re
from ruyaml import YAML

def _load_audit_appendix(audit_path: Path) -> dict[str, Any]:
    """Extract and parse the fenced ```yaml block from 20-AUDIT.md.

    Mirrors arrconf.audit.verify_audit:925-943.
    """
    text = audit_path.read_text(encoding="utf-8")
    yaml_block = re.search(r"```yaml\n(.*?)\n```", text, re.DOTALL)
    if not yaml_block:
        log.error("audit_missing_yaml_appendix", input=str(audit_path))
        sys.exit(2)
    yaml = YAML(typ="safe")
    try:
        return yaml.load(yaml_block.group(1)) or {}
    except Exception as exc:
        log.error("audit_yaml_parse_error", error=str(exc))
        sys.exit(2)
```

**Use `ruyaml` not `pyyaml`** — same dependency as arrconf (already in `pyproject.toml`), and round-trip safe.

---

#### 5. State persistence — atomic write via tempfile + rename

**No project analog** (arrconf is stateless per CONTEXT §"Established Patterns"). Standard Python pattern:

```python
def _load_state(state_path: Path) -> dict[str, Any]:
    """Load resume state from JSON (or seed empty)."""
    if not state_path.exists():
        return {"completed": {"radarr": [], "sonarr": [], "qbittorrent": []}}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        log.error("state_file_corrupt", path=str(state_path), error=str(exc))
        sys.exit(2)

def _save_state(state: dict[str, Any], state_path: Path) -> None:
    """Atomic write: write to tempfile in same dir, then os.rename (POSIX atomic)."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=state_path.parent,
        prefix=".migration-state.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=True)
        os.rename(tmp, state_path)  # atomic on POSIX
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise
```

**State layout** (CONTEXT §"D-21-ORDER-02"):
```json
{
  "completed": {
    "radarr": [1, 2, 3, 4, 5],
    "sonarr": [1, 2, 7, 9, 10],
    "qbittorrent": ["aaaa1234", "bbbb5678", ...]
  },
  "started_at": "2026-05-26T14:30:00Z"
}
```

The state file MUST be in `.gitignore` (add `.migration-state.json` and `.migration-state.*.tmp`).

---

#### 6. Halt-on-error per-item loop — try/except + sys.exit(1)

**Analog:** `tools/arrconf/arrconf/reconcilers/qbittorrent.py` lines 130-200 (per-action loop with `actions_taken` list). Adapted for halt-on-first-error per D-21-FAIL-01:

```python
def _migrate_radarr_items(
    radarr: RadarrClient,
    items: list[dict[str, Any]],
    tag_label_to_id: dict[str, int],
    state: dict[str, Any],
    state_path: Path,
    *,
    dry_run: bool,
) -> list[int]:
    """Per-item migrate loop with halt-on-first-error.

    For each movie in audit['radarr']['movies_to_migrate']:
      1. Skip if id in state['completed']['radarr']
      2. If action == 'move_and_retag': os.rename(current_path → target path)
      3. PUT /api/v3/movie/{id} with body {rootFolderPath, path, tags: <resolved ids>}
      4. Append id to state['completed']['radarr'], _save_state(...)

    On exception: log + sys.exit(1). Operator diagnoses, fixes, --resume.
    """
    migrated_ids: list[int] = []
    completed: list[int] = state["completed"]["radarr"]

    for movie in items:
        mid = movie["id"]
        if mid in completed:
            log.info("skip_already_completed", app="radarr", id=mid, title=movie["title"])
            continue

        to_block = movie.get("to") or {}
        action = to_block.get("action")
        target_rfp = to_block.get("rootFolderPath", "")
        target_tag_labels: list[str] = to_block.get("tags", [])
        current_path = movie.get("current_path", "")

        try:
            # Step 1 — filesystem mv (only if move_and_retag)
            if action == "move_and_retag" and not dry_run:
                new_path = current_path.replace(movie["current_rootFolder"], target_rfp)
                log.info("fs_move", app="radarr", id=mid, src=current_path, dst=new_path)
                os.rename(current_path, new_path)  # atomic on same filesystem
            elif action == "move_and_retag" and dry_run:
                log.info("dry_run_fs_move", app="radarr", id=mid, src=current_path, target=target_rfp)

            # Step 2 — Radarr PUT (resolve tag labels → IDs via tag_label_to_id)
            target_tag_ids = [
                tag_label_to_id[label]
                for label in target_tag_labels
                if label in tag_label_to_id
            ]
            put_body = {
                "rootFolderPath": target_rfp,
                "tags": target_tag_ids,
                # path will be computed by Radarr from rootFolderPath + title
            }
            if dry_run:
                log.info("dry_run_radarr_put", id=mid, body=put_body)
            else:
                # Radarr requires full body on PUT — fetch first, mutate, PUT
                current_body = radarr.get(f"/movie/{mid}")
                current_body["rootFolderPath"] = target_rfp
                current_body["tags"] = target_tag_ids
                current_body["path"] = current_body["path"].replace(
                    movie["current_rootFolder"], target_rfp
                )
                radarr.put("/movie", id=mid, json=current_body)

            # Step 3 — mark completed, persist state immediately
            completed.append(mid)
            state["completed"]["radarr"] = completed
            if not dry_run:
                _save_state(state, state_path)
            migrated_ids.append(mid)

        except (ApiClientError, AuthError, ServerError, OSError) as exc:
            log.error(
                "migration_halt",
                app="radarr",
                id=mid,
                title=movie.get("title", ""),
                step=action,
                error=str(exc),
                hint="Snapshot forensic, diagnose, fix, --resume",
            )
            sys.exit(1)

    return migrated_ids
```

**Key reuse point — `radarr.put()`** is from `_ArrV3Client.put` (lines 123-133 in `client_base.py`) which **automatically sets `forceSave=true`** (ADR-8). This is critical: without `forceSave`, Radarr's UI-grade pre-save validation rejects the request because the API key in the cluster body is masked.

---

#### 7. Refresh batch — single POST `/command` per app (D-21-ORDER-03)

**No exact analog** (no current arrconf code does `/command` POST), but the pattern is the standard Sonarr/Radarr v3 idiom:

```python
def _batch_refresh_radarr(radarr: RadarrClient, movie_ids: list[int], *, dry_run: bool) -> None:
    """Single POST /api/v3/command to refresh all migrated movies at once."""
    if not movie_ids:
        log.info("refresh_skip", app="radarr", reason="no migrated movies")
        return
    body = {"name": "RefreshMovie", "movieIds": movie_ids}
    if dry_run:
        log.info("dry_run_radarr_refresh", body=body)
        return
    radarr.post("/command", json=body)
    log.info("refresh_complete", app="radarr", count=len(movie_ids))

def _batch_refresh_sonarr(sonarr: SonarrClient, series_ids: list[int], *, dry_run: bool) -> None:
    """Single POST /api/v3/command to refresh all migrated series at once."""
    if not series_ids:
        log.info("refresh_skip", app="sonarr", reason="no migrated series")
        return
    body = {"name": "RefreshSeries", "seriesIds": series_ids}
    if dry_run:
        log.info("dry_run_sonarr_refresh", body=body)
        return
    sonarr.post("/command", json=body)
    log.info("refresh_complete", app="sonarr", count=len(series_ids))
```

`radarr.post()` and `sonarr.post()` are inherited from `ArrApiClient.post` (lines 97-99 in `client_base.py`).

---

#### 8. qBit setLocation + setCategory loop — `post_form` reuse

**Analog:** `tools/arrconf/arrconf/reconcilers/qbittorrent.py` lines 143-198 (`client.post_form` with form-encoded body). The qBit WebUI uses `/api/v2/torrents/setLocation` and `/api/v2/torrents/setCategory` with form-encoded `hashes=…&location=…` or `hashes=…&category=…`:

```python
def _migrate_qbit_torrents(
    qbit: QbittorrentClient,
    torrents: list[dict[str, Any]],
    state: dict[str, Any],
    state_path: Path,
    *,
    dry_run: bool,
) -> int:
    """Per-torrent setLocation + setCategory with halt-on-error.

    Skips orphans flagged `to.save_path == 'PRUNE_PHASE_22'` (D-21-QBIT-03).
    """
    migrated = 0
    completed: list[str] = state["completed"]["qbittorrent"]

    for t in torrents:
        hash_ = t["hash"]
        if hash_ in completed:
            log.info("skip_already_completed", app="qbit", hash=hash_[:12])
            continue

        to_block = t.get("to") or {}
        new_location = to_block.get("save_path", "")

        # D-21-QBIT-03 — skip orphans
        if new_location == "PRUNE_PHASE_22":
            log.info("skip_orphan", hash=hash_[:12], name=t.get("name", "")[:60])
            continue

        # Derive new category from save_path (/data/torrents/<cat> → <cat>)
        new_category = new_location.removeprefix("/data/torrents/").rstrip("/")

        try:
            if dry_run:
                log.info(
                    "dry_run_qbit_setLocation",
                    hash=hash_[:12],
                    location=new_location,
                    category=new_category,
                )
            else:
                # D-21-QBIT-01 — direct setLocation, no pause/resume
                qbit.post_form(
                    "/torrents/setLocation",
                    data={"hashes": hash_, "location": new_location},
                )
                # D-21-QBIT-02 — setCategory immediately after
                qbit.post_form(
                    "/torrents/setCategory",
                    data={"hashes": hash_, "category": new_category},
                )

            completed.append(hash_)
            state["completed"]["qbittorrent"] = completed
            if not dry_run:
                _save_state(state, state_path)
            migrated += 1

        except (ApiClientError, AuthError) as exc:
            log.error(
                "migration_halt",
                app="qbittorrent",
                hash=hash_[:12],
                name=t.get("name", "")[:60],
                error=str(exc),
                hint="Snapshot forensic, diagnose, fix, --resume",
            )
            sys.exit(1)

    return migrated
```

---

#### 9. Jellyfin global refresh — single `POST /Library/Refresh`

**No analog** — Jellyfin reconciler in `arrconf/reconcilers/jellyfin.py` does library CRUD via `/Library/VirtualFolders`, not refresh. New pattern, simple:

```python
def _refresh_jellyfin(jellyfin: JellyfinClient, *, dry_run: bool) -> None:
    """Single global /Library/Refresh — D-21-JF-01.

    Single-user homelab accepts watch-state best-effort (CLAUDE.md filesystem
    migration runbook precedent). The 10 Category libs should keep ItemCount > 0
    post-refresh per ROADMAP SC#5.
    """
    if dry_run:
        log.info("dry_run_jellyfin_refresh")
        return
    # JellyfinClient inherits .post() from ArrApiClient but Jellyfin's
    # /Library/Refresh returns 204 with empty body — ArrApiClient.post calls
    # .json() which would fail. Call _request directly to bypass the .json() decode.
    jellyfin._request("POST", "/Library/Refresh")
    log.info("jellyfin_refresh_dispatched")
```

**Pitfall — Jellyfin 204 response:** `ArrApiClient.post` (line 97-99) calls `.json()` on the response. Jellyfin's `/Library/Refresh` returns HTTP 204 with empty body, which causes `json.JSONDecodeError`. Use `_request("POST", ...)` directly to bypass the `.json()` step. This mirrors `arrconf/reconcilers/jellyfin.py`'s pattern where 204 endpoints are handled with raw `_request` calls.

---

#### 10. Tag label → ID resolution upfront

**Analog:** `tools/arrconf/arrconf/__main__.py` lines 43-95 (`_resolve_seerr_anime_tag_ids`) — GET `/tag`, build `label → id` map, resolve. Adapt:

```python
def _build_tag_label_to_id(client: SonarrClient | RadarrClient) -> dict[str, int]:
    """Fetch /tag once, build label→id map.

    Mirrors arrconf/__main__.py:74-82 — single GET, build lookup, reuse N times.
    """
    raw_tags: list[dict[str, Any]] = client.get("/tag")
    return {t["label"]: int(t["id"]) for t in raw_tags if "label" in t and "id" in t}
```

Call this once at the start of `_migrate_radarr_items` / `_migrate_sonarr_items`, pass the dict in. The audit's `to.tags` field is a list of **labels** (not IDs); migrate resolves them to IDs for the PUT body.

---

#### 11. Main entry point — orchestration

```python
def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    # Logging level
    import logging
    level = logging.DEBUG if args.verbose else logging.INFO
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(level))

    # 1. Load audit YAML appendix
    audit = _load_audit_appendix(args.audit)
    log.info(
        "audit_loaded",
        radarr_count=len(audit.get("radarr", {}).get("movies_to_migrate", [])),
        sonarr_count=len(audit.get("sonarr", {}).get("series_to_migrate", [])),
        qbit_count=len(audit.get("qbittorrent", {}).get("torrents_to_relocate", [])),
    )

    # 2. Determine targets (all apps present in audit)
    targets = {
        app for app in ("radarr", "sonarr", "qbittorrent", "jellyfin")
        if app in audit
    }

    # 3. Pre-flight env-var gate
    _check_env_vars(targets)

    # 4. Load resume state
    state = _load_state(args.state_file)

    # 5. Build clients (URLs default to localhost — operator port-forwards beforehand)
    radarr = RadarrClient(
        base_url=os.environ.get("RADARR_URL", "http://localhost:7878"),
        api_key=os.environ["RADARR_API_KEY"],
    ) if "radarr" in targets else None
    sonarr = SonarrClient(
        base_url=os.environ.get("SONARR_URL", "http://localhost:8989"),
        api_key=os.environ["SONARR_API_KEY"],
    ) if "sonarr" in targets else None
    qbit = QbittorrentClient(
        base_url=os.environ.get("QBT_URL", "http://localhost:8080"),
        username=os.environ["QBT_USER"],
        password=os.environ["QBT_PASS"],
    ) if "qbittorrent" in targets else None
    jellyfin = JellyfinClient(
        base_url=os.environ.get("JELLYFIN_URL", "http://localhost:8096"),
        api_key=os.environ["JELLYFIN_API_KEY"],
    ) if "jellyfin" in targets else None

    # 6. Execute per-app migrate loops
    radarr_migrated: list[int] = []
    sonarr_migrated: list[int] = []
    if radarr:
        radarr_tag_map = _build_tag_label_to_id(radarr)
        radarr_migrated = _migrate_radarr_items(
            radarr,
            audit["radarr"]["movies_to_migrate"],
            radarr_tag_map,
            state,
            args.state_file,
            dry_run=args.dry_run,
        )
    if sonarr:
        sonarr_tag_map = _build_tag_label_to_id(sonarr)
        sonarr_migrated = _migrate_sonarr_items(
            sonarr,
            audit["sonarr"]["series_to_migrate"],
            sonarr_tag_map,
            state,
            args.state_file,
            dry_run=args.dry_run,
        )

    # 7. Batched refresh per app (D-21-ORDER-03)
    if radarr:
        _batch_refresh_radarr(radarr, radarr_migrated, dry_run=args.dry_run)
    if sonarr:
        _batch_refresh_sonarr(sonarr, sonarr_migrated, dry_run=args.dry_run)

    # 8. qBit setLocation + setCategory loop
    if qbit:
        _migrate_qbit_torrents(
            qbit,
            audit["qbittorrent"]["torrents_to_relocate"],
            state,
            args.state_file,
            dry_run=args.dry_run,
        )

    # 9. Jellyfin global refresh (D-21-JF-01)
    if jellyfin:
        _refresh_jellyfin(jellyfin, dry_run=args.dry_run)

    log.info(
        "migration_complete",
        radarr=len(radarr_migrated),
        sonarr=len(sonarr_migrated),
        dry_run=args.dry_run,
    )
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

---

### `21-RUNBOOK.md` (runbook, documentation)

**Analog:** `CLAUDE.md §"Filesystem migration: v0.2.0 flat → v0.3.0 Categories"` — lines 518-605.

**Verbatim section structure to mirror:**

```markdown
# 21-RUNBOOK — Categories cleanup migration (Phase 21)

Procédure operator-driven pour exécuter le plan déterministe `20-AUDIT.md`.
Discipline ADR-6 : snapshot AVANT et APRÈS, lossless, versionné dans Git.

## Pré-requis

- 20-AUDIT.md verify-gate exit 0 (déjà validé en Phase 20)
- `kubectl` accès au cluster
- NAS monté à `/mnt/nas/media-stack/` (perms 777, NFS export permissif)
- `uv` installé pour exécuter `migrate-categories.py`

## Étape 1 — Pre-check (snapshot baseline)

\`\`\`bash
# 1. Snapshot baseline avant toute mutation
tools/snapshot/snapshot.sh --output snapshots/before-categories-cleanup-$(date +%F)/
git add snapshots/before-categories-cleanup-* && git commit -m "snapshot(pre-categories-cleanup): baseline"

# 2. Vérifier que les 10 /media/<category> dirs existent (déjà créés en Phase 9)
ls /mnt/nas/media-stack/media/ | sort
\`\`\`

## Étape 2 — Port-forwards + credentials

\`\`\`bash
# Port-forwards (4 apps)
kubectl -n selfhost port-forward svc/radarr 7878:7878 &
kubectl -n selfhost port-forward svc/sonarr 8989:8989 &
kubectl -n selfhost port-forward svc/qbittorrent 8080:8080 &
kubectl -n selfhost port-forward svc/jellyfin 8096:8096 &

# Extract sealed-secret arrconf-env (même pattern que Phase 20 Task 6)
eval "$(kubectl -n selfhost get secret arrconf-env -o json \
  | jq -r '.data | to_entries[] | "export \(.key)=\(.value | @base64d)"')"
\`\`\`

## Étape 3 — Dry-run (mandatory)

\`\`\`bash
uv run python tools/scripts/migrate-categories.py \
  --audit .planning/phases/20-categories-cleanup-audit/20-AUDIT.md \
  --dry-run

# Review output: confirm action lines match expectations. No "halt" events expected.
\`\`\`

## Étape 4 — Apply

\`\`\`bash
uv run python tools/scripts/migrate-categories.py \
  --audit .planning/phases/20-categories-cleanup-audit/20-AUDIT.md \
  --apply
\`\`\`

Si halt-on-error : voir §Troubleshooting.

## Étape 5 — Post-check (snapshot + diff)

\`\`\`bash
tools/snapshot/snapshot.sh --output snapshots/after-categories-cleanup-$(date +%F)/
diff -r snapshots/before-categories-cleanup-* snapshots/after-categories-cleanup-*

# Attendu : changements uniquement sur rootFolderPath / path / tags des items audit,
#          + save_path / category des 37 torrents. Toute autre divergence = anomalie.

git add snapshots/after-categories-cleanup-* && git commit -m "snapshot(post-categories-cleanup)"

# Sanity check : 20-AUDIT.md verify-gate doit toujours passer
uv run --project tools/arrconf arrconf audit-verify \
  -i .planning/phases/20-categories-cleanup-audit/20-AUDIT.md
\`\`\`

## Troubleshooting

### Le script halt avec une exception API 4xx

\`\`\`bash
# Snapshot forensic immédiat (NE PAS DIFFÉRER)
tools/snapshot/snapshot.sh --output snapshots/forensic-$(date +%FT%H%M)/

# Diagnose : lire la dernière ligne migration_halt dans les logs structlog
# Fixer le root cause (souvent : tag label not found, path inexistant)
# Re-lancer — state.json skip les items déjà completed
uv run python tools/scripts/migrate-categories.py --audit ... --apply
\`\`\`

### Une lib Jellyfin se retrouve vide après refresh

Investigate via API : `GET /Library/VirtualFolders` → check ItemCount par lib.
Si une lib est vide, lancer un rescan manuel ciblé via UI Jellyfin.

### Rollback

Pas de script rollback automatique. Si nécessaire :
- API mutations : opérateur reverse manuellement via UI Radarr/Sonarr (rootFolderPath modifié sur les ids listés dans state.json)
- Filesystem : `mv` inverse depuis `/mnt/nas/media-stack/media/<new>/` vers `/media/<old>/`
- qBit : setLocation inverse via UI ou nouveau script `migrate-categories-rollback.py` (ad-hoc)

Cf. snapshot pre-categories-cleanup pour l'état exact à restaurer.
```

**Style notes (matching CLAUDE.md §Filesystem migration):**
- French (project convention for operator-facing docs)
- Numbered `## Étape N — Title` sections (verbatim from CLAUDE.md analog)
- Fenced bash blocks with inline comments
- Final "Notes" or "Troubleshooting" addendum
- Reference ADR-6 + the snapshot.sh tool by name

---

### `.migration-state.json` (state file)

**No analog** — pure data file produced/consumed by the script.

**Shape (locked by §"State persistence" pattern above):**
```json
{
  "completed": {
    "radarr": [],
    "sonarr": [],
    "qbittorrent": []
  },
  "started_at": "2026-05-26T14:30:00Z"
}
```

**Gitignore entry to add** (modification to `.gitignore`):
```
.migration-state.json
.migration-state.*.tmp
```

---

### `snapshots/before-categories-cleanup-YYYY-MM-DD/` + `…/after-…`

**Analog (exact):** every existing `snapshots/before-phase-N-YYYY-MM-DD/` directory (e.g. `snapshots/before-phase-16-2026-05-24/`).

**Pattern (zero new code):** invocation of `tools/snapshot/snapshot.sh --output snapshots/…/` per §Pre-check and §Post-check of the runbook above. The tool already exists, already covers 6 apps (sonarr/radarr/prowlarr/qbittorrent/seerr/jellyfin), and emits sanitized JSON dumps.

---

## Shared Patterns

### Halt-on-first-error
**Source:** `tools/arrconf/arrconf/reconcilers/sonarr.py` + Phase 21 D-21-FAIL-01
**Apply to:** every per-item migration loop (Radarr, Sonarr, qBit)
**Pattern:**
```python
try:
    # ... mutation ...
    completed.append(id)
    _save_state(state, state_path)
except (ApiClientError, AuthError, ServerError, OSError) as exc:
    log.error("migration_halt", app=..., id=..., error=str(exc), hint="...")
    sys.exit(1)
```

State is persisted **immediately after each successful item** so a halt mid-loop loses zero progress.

### Env-var fail-fast pre-flight
**Source:** `tools/arrconf/arrconf/__main__.py` lines 217-235
**Apply to:** `_check_env_vars()` at script start, BEFORE any cluster contact
**Pattern:** collect required env names per target app, check `os.environ.get(name).strip()`, sys.exit(2) with `log.error("missing_env_vars", missing=[...])` listing all missing in one error event.

### Exit code contract
**Source:** `tools/arrconf/arrconf/__main__.py` docstring lines 1-8
**Apply to:** every `sys.exit(...)` call in the script
**Pattern:**
- `0` — success / dry-run completed
- `1` — runtime failure (API or filesystem error during apply)
- `2` — config error (missing env, missing audit file, malformed YAML)

### Structured logging via structlog
**Source:** `tools/arrconf/arrconf/audit.py:30` (`log = structlog.get_logger()`)
**Apply to:** every log call in the script
**Pattern:** `log.info("event_name", key1=value1, key2=value2)` — never `log.info(f"event {value}")`. Event names are snake_case verbs (`fs_move`, `radarr_put`, `migration_halt`, `dry_run_qbit_setLocation`).

### YAML parsing (ruyaml + regex extraction)
**Source:** `tools/arrconf/arrconf/audit.py:925-943` (`verify_audit`)
**Apply to:** `_load_audit_appendix()` in the script
**Pattern:** read file as text, `re.search(r"\`\`\`yaml\n(.*?)\n\`\`\`", text, re.DOTALL)`, parse the matched group via `YAML(typ="safe").load(...)`, exit(2) on either gate failure.

### Client reuse via path-injection
**Source:** CONTEXT §"Reusable Assets" + RESEARCH-less guidance
**Apply to:** module header
**Pattern:**
```python
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "arrconf"))
from arrconf.client_base import RadarrClient, SonarrClient, QbittorrentClient, JellyfinClient
```

This reuses **all** the battle-tested HTTP machinery (tenacity retry, 401/404 classification, `forceSave=true` on PUTs, qBit cookie auth, Jellyfin MediaBrowser header) without packaging the script in `arrconf/`.

### Dry-run discipline
**Source:** `tools/arrconf/arrconf/reconcilers/qbittorrent.py:139-141` (every action branch checks `if dry_run: log.info("dry_run_skip", ...)`)
**Apply to:** every mutation call site (os.rename, radarr.put, sonarr.put, qbit.post_form, jellyfin._request)
**Pattern:**
```python
if dry_run:
    log.info("dry_run_<action>", **context)
else:
    client.<action>(...)
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `.migration-state.json` | state | file-I/O | Project has no precedent — arrconf is stateless. New pattern: atomic tempfile + os.rename, JSON Lines NOT used (single document suffices). |

**Implication for planner:** the planner should NOT search for an existing state-file pattern — it doesn't exist. Use the `_load_state` / `_save_state` skeleton from §5 above verbatim.

---

## Critical Deltas vs Analogs (executor must honor)

| Decision | Phase 20 analog default | Phase 21 deviation | Source |
|----------|-------------------------|--------------------|---------|
| Tool location | `tools/arrconf/` (packaged) | **`tools/scripts/`** (throwaway) | D-21-TOOL-01 |
| Chart-pin co-bump | arrconf code change → `values.yaml#arrconf.image.tag` bump same commit | **NO bump** — script hors arrconf, not in image | D-21-TOOL-02 |
| Test obligation | ≥15 respx tests, 70% coverage gate | **No tests required**; triade Python optional for readability | D-21-TOOL-03 |
| CLI framework | Typer (project standard for arrconf subcommands) | **argparse** (4 flags, no need for Typer) | CONTEXT §"Established Patterns" |
| Read/write posture | audit is read-only invariant (grep `\.(post\|put)` returns 0) | **Mutating** — PUT, POST, post_form per-item | D-21-ORDER-01 |
| Failure mode | continue-on-error per-app (arrconf reconcilers) | **Halt-on-first-error** per-item | D-21-FAIL-01 |
| State | stateless (re-reads cluster each run) | **state.json resume** with atomic write | D-21-ORDER-02 |
| Jellyfin endpoint | `/Library/VirtualFolders` (CRUD) | **`/Library/Refresh`** (1 global POST) | D-21-JF-01 |
| qBit posture | declarative CRUD on categories | **direct setLocation+setCategory** in same loop | D-21-QBIT-01 / D-21-QBIT-02 |

---

## Metadata

**Analog search scope:**
- `/data/projets/perso/arr-stack/tools/arrconf/` (full module: client_base, audit, __main__, reconcilers, settings, exceptions)
- `/data/projets/perso/arr-stack/tools/scripts/` (existing bash scripts)
- `/data/projets/perso/arr-stack/tools/snapshot/` (snapshot.sh)
- `/data/projets/perso/arr-stack/.planning/phases/20-categories-cleanup-audit/` (predecessor phase artefacts)
- `/data/projets/perso/arr-stack/CLAUDE.md` (filesystem migration runbook narrative analog)

**Files scanned (read):** 8 — audit.py, __main__.py, client_base.py, settings.py, _shared.py, qbittorrent.py reconciler, snapshot.sh, 20-AUDIT.md (YAML appendix sample), check-renovate-annotations.sh

**Files scanned (grep only):** ~12 — Sonarr/Radarr/Jellyfin reconcilers for `RefreshMovie` / `setLocation` / `/Library/Refresh` patterns (none found — these are net-new API verbs for Phase 21).

**Pattern extraction date:** 2026-05-26
