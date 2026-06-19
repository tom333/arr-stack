# arr-dashboard — Stall diagnostics design spec

**Date:** 2026-06-19
**Status:** Design approved (brainstorming) — pending spec review → writing-plans
**Builds on:** arr-dashboard V2.x (read-only chain + flags + recovery actions).

## Goal

When a download isn't progressing, tell the operator **why** — distinguishing a
tracker-side block (e.g. C411 returning `Forbidden` on a low ratio) from a genuinely
dead torrent (no seeders), from queued/metadata states. Today the dashboard shows a
coarse `bloque` flag (and not even that for some stuck downloads), with no cause. The
operator can't tell a *recoverable* stall (ratio — don't delete, feed ratio) from a
*dead* one (no source — delete and re-grab).

## Motivating case (verified live, 2026-06-19)

`Project Hail Mary` (tmdb 687163) on C411, stuck at 0%:
- `/torrents/info`: `state=forcedDL, dlspeed=0, progress=0, num_seeds=0, num_complete=0, num_leechs=0, ratio=0, eta=8640000` (qBit's ∞ placeholder), `tracker=""` (empty — no working tracker).
- `/torrents/trackers?hash=…`: the real tracker entry is `status=4` (not working), `msg='Forbidden'`, `url=https://c411.org/announce/…`.

Two findings that shape the design:
1. **The cause lives in the tracker entry, not `/torrents/info`.** When the tracker
   rejects the announce, `/torrents/info.tracker` is empty; the status+msg only appear
   via `/torrents/trackers?hash=X` (one extra call per torrent).
2. **This case is NOT flagged `bloque`.** The `bloque` flag fires on qBit state ∈
   {`stalledDL`,`missingFiles`,`error`}; this download is `forcedDL`. So the diagnostic
   must be an **independent signal**, not an enrichment of `bloque`, or it misses the
   exact case that motivated it.

## Non-goals

- No recovery actions (re-announce, re-check, grab-cancel, feed-ratio) — that is the
  separate V2.2 actions scope. This feature is **read-only diagnostics**.
- No tracker-name knowledge base / ratio-rule mapping. Labels are **generic and honest**
  — we surface the raw tracker `msg` (`Forbidden`) + host (`c411.org`), we do NOT assert
  "ratio too low" (C411 only says `Forbidden`; asserting ratio would be a guess).
- No alerting/notifications. No persistence/history of stall age beyond what qBit reports.

---

## Architecture

arr-dashboard-only. No `tools/arrconf` change: the per-torrent tracker fetch uses the
existing public `QbittorrentClient.get(...)` method — no new client method → **no arrconf
image co-bump**.

```
tools/arr-dashboard/arr_dashboard/
  sources.py        # fetch_all: for STALLED torrents only, fetch /torrents/trackers and
                    #            attach the worst tracker entry onto the torrent dict
  models.py         # Download += qBit stat fields + tracker_status/msg/host
  correlate.py      # _to_download: map the new info fields + attached tracker info
  diagnostics.py    # NEW, pure: diagnose_stall(download) -> StallDiagnosis | None
```

### Stall detection

A download is **stalled** when `dl_speed == 0 and progress < 1.0`. (Catches `forcedDL`
at 0% — the C411 case — which the `bloque` flag misses; also catches `stalledDL` etc.)
A download with `dl_speed > 0` is progressing → no diagnosis.

### Tracker fetch (in `sources.fetch_all`)

After `list_torrents()`, for each torrent that is stalled (`dlspeed==0 and progress<1`):
- call `qbit.get(f"/torrents/trackers?hash={hash}")` (reuses the same logged-in client).
- skip pseudo-rows whose `url` starts with `**` (`** [DHT] **`, `** [PeX] **`, `** [LSD] **`).
- pick the **worst** real tracker entry to attach (priority: a `status==4` entry with a
  non-empty `msg` wins; else the first real entry). Attach as `t["_tracker"] = {status, msg, host}`
  where `host` is the URL's hostname (`urllib.parse.urlsplit(url).hostname`).
- **Graceful**: any exception on this call is swallowed (log debug) and the torrent keeps
  no `_tracker` — the refresh must never fail because of tracker probing. Non-stalled
  torrents are never probed (bounds the extra calls to the handful that are stuck).

qBit tracker `status` codes (for reference): `0` disabled, `1` not contacted yet,
`2` working, `3` updating, `4` not working/error.

### Classification (`diagnostics.py`, pure)

```python
class StallDiagnosis(BaseModel):
    cause: str       # machine key: "metadata" | "queued" | "tracker-refused" | "no-source" | "stalled"
    label: str       # short FR label for the row tag, e.g. "tracker refuse: Forbidden"
    host: str | None # tracker host when relevant, e.g. "c411.org"
    recoverable: bool # True for tracker-refused/queued/metadata; False for no-source

def diagnose_stall(d: Download) -> StallDiagnosis | None:
    # returns None when not stalled (dl_speed>0 or progress>=1.0 or dl_speed is None)
```

Priority order inside `diagnose_stall` (first match wins):
1. `state == "metaDL"` → cause `metadata`, label "métadonnées", recoverable True.
2. `state == "queuedDL"` → cause `queued`, label "en file qBit", recoverable True.
3. `tracker_status == 4` and `tracker_msg` non-empty → cause `tracker-refused`,
   label `f"tracker refuse: {tracker_msg}"`, host = `tracker_host`, recoverable True.
4. trackers reachable (`tracker_status in (2, 3)` or no tracker info) **and**
   `num_complete == 0` → cause `no-source`, label "aucun seed", recoverable False.
5. fallback → cause `stalled`, label "bloqué (cause inconnue)", recoverable True (don't
   assume dead when we can't tell).

### Data model (`models.py`)

`Download` gains optional fields (all default `None`, populated from qBit when present):
`dl_speed: int | None`, `eta: int | None`, `num_seeds: int | None`,
`num_complete: int | None`, `num_leechs: int | None`, `num_incomplete: int | None`,
`ratio: float | None`, `added_on: int | None` (epoch seconds),
`tracker_status: int | None`, `tracker_msg: str | None`, `tracker_host: str | None`.

`correlate._to_download` maps `/torrents/info` keys (`dlspeed`→`dl_speed`, `eta`,
`num_seeds`, `num_complete`, `num_leechs`, `num_incomplete`, `ratio`, `added_on`) and the
attached `_tracker` dict (`status`→`tracker_status`, `msg`→`tracker_msg`, `host`→`tracker_host`).

The classification **logic** lives only in the pure `diagnose_stall` function (one tested
place). `correlate._to_download` calls it once per download and stores the result on
`Download.diagnosis: StallDiagnosis | None`, so it is computed server-side, serialized into
the row JSON for free, and the frontend stays dumb (renders the label, no logic). The pure
function takes the raw fields and returns the diagnosis; storing its output on the model is
not duplicated logic.

---

## UI (`web/src/`)

Both the row tag and the expandable detail (per the brainstorm decision).

- **api.ts**: extend `Download` with the new fields + `diagnosis: { cause, label, host, recoverable } | null`.
- **App.svelte** (main table): for a row with any download whose `diagnosis` is set, show a
  compact cause tag near the flags cell, e.g. `tracker refuse (c411.org)` / `aucun seed` /
  `en file qBit`. Color by `recoverable`: amber for recoverable (ratio/queued/metadata),
  red for `no-source` (dead). If multiple downloads, show the worst (non-recoverable first).
- **RowDetail.svelte** (expand): per download, a small metrics block:
  - vitesse (`dl_speed` → human B/s), ETA (`eta` → human, ∞ when `eta>=8640000`),
  - seeds/peers (`num_complete` seeders / `num_leechs` peers; `num_seeds`/`num_incomplete`
    = connected), ratio, âge (`added_on` → "depuis 14h / 3j"),
  - tracker line: `status` (working/not working) + `msg` + `host` when present.

No new ConfirmDialog/actions (read-only).

---

## Error handling / edge cases

- qBit creds absent → no qbit client → no downloads → no diagnoses (unchanged graceful path).
- `/torrents/trackers` call fails for a torrent → that torrent has no tracker info →
  `diagnose_stall` falls through to `no-source` or `stalled` (never crashes).
- `eta == 8640000` (qBit ∞) → render "∞", not "100 jours".
- A download that is complete (`progress>=1.0`) or actively downloading (`dl_speed>0`) →
  `diagnose_stall` returns `None` → no tag, no metrics-stall styling.
- Momentary `dl_speed==0` between pieces could transiently flag a healthy download; the
  30s refresh self-corrects on the next snapshot. Acceptable; no debounce in v1.

---

## Testing

- **`diagnostics.py`** (≥90%): one test per cause branch (metadata, queued, tracker-refused
  with C411-like `status=4`+`Forbidden`, no-source, stalled-fallback) + the not-stalled
  (`dl_speed>0` and `progress>=1.0`) → `None` cases.
- **`sources`**: tracker fetch happens only for stalled torrents (assert no
  `/torrents/trackers` call for a `dl_speed>0` torrent); graceful degradation when the
  trackers call errors (respx 500 → torrent still present, no `_tracker`).
- **`correlate`**: new fields mapped from a realistic `/torrents/info` fixture incl. the
  `_tracker` attachment; `diagnosis` set on a stalled download.
- Coverage ≥70% gate; Python triad (ruff + mypy) + frontend `npm run build` + `npm run check`.

## Deploy

arr-dashboard-only (no `tools/arrconf`) → bump only `arr-dashboard.image.tag`. `feat:` →
minor → next tag from latest (≈ `v0.38.0`; recompute at release from the highest
conventional-commit type since the last tag — a `feat:` release-pin commit forces minor).
Same lockstep: push main → chart-lint auto-tags + dispatches the arr-dashboard image →
verify GHCR manifest → bump my-kluster `targetRevision` → hard-refresh app-of-apps → verify pod.

## Out of scope / future

Recovery actions on the diagnosis (re-announce, re-check, grab-cancel, pause ratio-blocked);
notifications when a download is stalled > N h; NAS/disk-health widget; bulk actions.
