# arrconf — Unmonitor imported items design spec

**Date:** 2026-06-19
**Status:** Design approved (brainstorming) — pending spec review → writing-plans

## Goal

Make Radarr/Sonarr show imported content as **not monitored**, so the operator's library
reads as "done" and there is zero re-grab/upgrade activity on completed items. Driven by a
confirmed operator preference: **no quality upgrades, no re-grab of owned content**.

Context (verified live 2026-06-19): all 18 quality profiles already have
`upgradeAllowed=false`, so quality upgrades are already disabled — but every item stays
`monitored=true` in the UI (30/30 Radarr movies; 17 have files). The operator wants those
flipped to unmonitored.

## Behavior

A new arrconf reconcile step, **gated by an intent toggle**, enforced on every `arrconf apply`
(the in-cluster CronJob):

- **Radarr** — `GET /movie`; collect `id` where `hasFile == true AND monitored == true`;
  if any, `PUT /movie/editor {"movieIds": [...], "monitored": false}`. No match → no-op.
- **Sonarr** — `GET /series`; for each series `GET /episode?seriesId={id}`; collect episode
  `id` where `hasFile == true AND monitored == true`; if any (across all series), one
  `PUT /episode/monitor {"episodeIds": [...], "monitored": false}`. **The series record stays
  `monitored=true`** so newly-aired episodes are still grabbed — only already-downloaded
  episodes are unmonitored. No match → no-op.

**Idempotent:** once flipped, the next run finds nothing (`monitored` already false) → 0 PUT.

**Enforcement every apply (operator-confirmed):** if the operator manually re-monitors an item
in the UI, the next apply re-unmonitors it. This is declared-state enforcement (consistent
with "no re-grab"). To force a re-grab of a corrupt/lost file, the operator disables the
toggle (or deletes + re-adds the item).

## Scope / frontier

`monitored` is *arr item state (like `tags`), squarely arrconf's domain — **not** configarr
(which owns quality_profiles / custom_formats / naming, ADR-5). This feature does NOT touch
any quality-profile definition; it only flips an item-level boolean. No frontier violation.

## Non-goals

- Unmonitoring whole Sonarr series (rejected — breaks ongoing-show episode grabbing).
- Any quality-profile change (upgrades are already off; not in scope).
- Re-monitoring / "exempt this item" tagging — out of scope (toggle off is the escape hatch).
- A dashboard surface for this — out of scope.

---

## Architecture

Mirrors the existing `category_quality_profiles` feature exactly (an intent-toggle-driven,
per-app reconcile step wired in `__main__`). All changes under `tools/arrconf/`.

### 1. `intent_config.py` — add the toggle to `IntentConfig`

Add a field beside `category_quality_profiles`:
```python
    unmonitor_imported: bool = Field(
        default=False,
        description=(
            "When true, `arrconf apply` unmonitors Radarr movies that have a file and "
            "Sonarr episodes that have a file (the series stays monitored so new episodes "
            "still grab). Enforced every apply (re-unmonitors manual re-monitors). "
            "Item-state only — never touches quality-profile definitions (ADR-5 safe)."
        ),
    )
```
`intent.yml` is mounted at runtime and loaded via `load_intent` into `intent_cfg` — the toggle
is read at reconcile time, NOT emitted into `arrconf.yml`.

### 2. `intent.yml` — set the toggle on

Add at the top level (sibling of `category_quality_profiles`):
```yaml
unmonitor_imported: true
```

### 3. New `arrconf/reconcilers/_unmonitor.py`

Two thin functions, each returning a list of action strings (mirrors the
`reconcile_category_profiles` return style):

```python
def unmonitor_imported_movies(client: Any, *, dry_run: bool) -> list[str]:
    """Unmonitor Radarr movies that already have a file (PUT /movie/editor)."""
    movies = client.get("/movie")
    ids = [m["id"] for m in movies if m.get("hasFile") and m.get("monitored")]
    if not ids:
        return ["unmonitor_movies:no-op"]
    if dry_run:
        return [f"unmonitor_movies:dry_run:{len(ids)}"]
    client._request("PUT", "/movie/editor", json={"movieIds": ids, "monitored": False})
    return [f"unmonitor_movies:applied:{len(ids)}"]


def unmonitor_downloaded_episodes(client: Any, *, dry_run: bool) -> list[str]:
    """Unmonitor Sonarr episodes that already have a file; series stays monitored."""
    series = client.get("/series")
    ep_ids: list[int] = []
    for s in series:
        episodes = client.get(f"/episode?seriesId={s['id']}")
        ep_ids.extend(e["id"] for e in episodes if e.get("hasFile") and e.get("monitored"))
    if not ep_ids:
        return ["unmonitor_episodes:no-op"]
    if dry_run:
        return [f"unmonitor_episodes:dry_run:{len(ep_ids)}"]
    client._request("PUT", "/episode/monitor", json={"episodeIds": ep_ids, "monitored": False})
    return [f"unmonitor_episodes:applied:{len(ep_ids)}"]
```

(`/movie/editor` and `/episode/monitor` are id-less PUTs → use `client._request("PUT", ...)`,
exactly as the existing `movie_tags`/`content_tags` steps do.)

### 4. `__main__.py` — wire the gated calls

In the Sonarr branch, right after the `reconcile_category_profiles(... "/series" ...)` loop,
add:
```python
            if intent_cfg is not None and intent_cfg.unmonitor_imported:
                from arrconf.reconcilers._unmonitor import (  # noqa: PLC0415
                    unmonitor_downloaded_episodes,
                )

                for act in unmonitor_downloaded_episodes(
                    client, dry_run=dry_run or settings.arrconf_dry_run
                ):
                    log.info("sonarr_unmonitor_action", action=act)
```
In the Radarr branch, right after the `reconcile_category_profiles(... "/movie" ...)` loop,
add the analogous block calling `unmonitor_imported_movies(radarr_client, dry_run=...)` with
`log.info("radarr_unmonitor_action", action=act)`.

### 5. Regenerate the intent schema

`intent_config` gained a field → regenerate `schemas/intent-schema.json` via
`arrconf intent-schema-gen --output ../../schemas/intent-schema.json` and commit (CI INTENT-01
checks reproducibility). `arrconf.yml` is unaffected (toggle is intent-only) so
`arrconf generate --check` (INTENT-03) stays green.

---

## Error handling / edge cases

- Toggle absent/false → step never runs (default `False`).
- Empty library / nothing with a file → `no-op` action, no PUT.
- A movie with `hasFile=false` (still wanted) → left monitored (correct; arr keeps searching
  for the missing requested item).
- Sonarr series with zero downloaded episodes → contributes no ids.
- `dry_run` (CI / `--dry-run`) → logs the count, issues no PUT.
- API failure on the GET/PUT → propagates as the usual `ApiClientError`/`ReconcileError` →
  the app is marked failed (exit 1) like any other reconcile step; other apps continue.

## Testing

- **`_unmonitor.py`** (respx, ≥90%):
  - `unmonitor_imported_movies`: mixed `/movie` (some hasFile+monitored, some hasFile-only-
    unmonitored, some no-file) → PUT body `movieIds` contains exactly the hasFile&monitored
    ids + `monitored:false`; all-already-unmonitored → no PUT (`no-op`); `dry_run` → no PUT.
  - `unmonitor_downloaded_episodes`: 2 series, per-series episodes → only hasFile&monitored
    episode ids in the PUT; series record never PUT; none → `no-op`; `dry_run` → no PUT.
- **wiring** (optional, light): with `intent_cfg.unmonitor_imported=False` the step is not
  invoked (no `/movie/editor` monitored PUT). Covered at the `__main__` level if a test exists;
  otherwise the unit tests + the toggle default suffice.
- Coverage ≥70% gate (95%+ on reconcilers per repo policy). Python triad (ruff + mypy).
  Confirm NEW mypy-error-count == 0 vs base (tests/ has pre-existing noise; gate is `mypy arrconf`).

## Deploy

Touches `tools/arrconf/**` → **co-bump `charts/arr-stack/values.yaml#arrconf.image.tag`
0.35.0 → 0.36.0 in the same commit** (release pin co-bump rule). Plus regenerate
`schemas/intent-schema.json`. Chart auto-tag → `feat:` → minor → next from latest (`v0.39.0`
→ **`v0.40.0`**; recompute at release). Same lockstep: push main → chart-lint auto-tags +
dispatches the arrconf image build at the new tag → verify `arrconf:0.36.0` on GHCR → bump
my-kluster `targetRevision` → hard-refresh app-of-apps → trigger a manual arrconf Job to
verify exit 0 (ArgoCD Healthy ≠ apply works — always verify the Job), then confirm live
Radarr movies flip to `monitored=false`.

## Out of scope / future

Series-level unmonitor for ended shows; per-item exempt tag; dashboard toggle; unmonitor on a
schedule independent of arrconf.
