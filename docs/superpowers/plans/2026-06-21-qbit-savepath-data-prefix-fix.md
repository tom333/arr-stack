# qBit savePath `/data/torrents/<name>` → `/data/<name>` Fix

> **For agentic workers:** surgical multi-site path fix. TDD per task. Steps use `- [ ]`.

**Goal:** Fix the qBit category savePath so Sonarr/Radarr can import downloads (closes the "From.S01 path does not exist" import failure).

**Root cause (dispositive):** Mounts: qBit hostPath `/media/data/torrents` → container `/data`; Sonarr/Radarr same hostPath → `/data/torrents`. So qBit `/data/<name>` == Sonarr `/data/torrents/<name>` (same bytes). The generator emits category savePath `/data/torrents/<name>` → qBit writes to `HOSTDIR/torrents/<name>`, reports `/data/torrents/<name>`; the live RPM `/data/<name>/`→`/data/torrents/<name>/` doesn't match → Sonarr reads `/data/torrents/<name>` (=HOSTDIR/<name>) where the file isn't → import fails. Correct path = `/data/<name>` (proven by mount physics, live Sonarr/Radarr RPMs, and `audit.py:314` torrent-alignment logic). The `/data/torrents/<name>` model is a regression in 3 code sites that also contradicts `audit.py` itself.

**Architecture:** Change the single source (`generate_qbit_categories` savePath) to `/data/<name>`; the qbit_manage `cat:` mapping auto-follows (it reads `cat.savePath`). Fix the two remaining hardcoded `/data/torrents` sites (intent.py root_dir/recycle_bin, audit.py expected-category-savePath) for internal consistency. Regenerate the two generated config files. Co-bump the arrconf image tag. Then migrate stranded live torrents via qBit Set-location.

**Tech stack:** Python 3.13, pydantic, pytest/respx, Helm, kubectl.

---

### Task 1: Fix `generate_qbit_categories` savePath

**Files:**
- Modify: `tools/arrconf/arrconf/generators/categories.py:131-137` (+ docstring lines 13, 134)
- Test: `tools/arrconf/tests/test_qbittorrent_categories.py:98-103`

- [ ] Update `test_savepath_format`: assert `zoe.savePath == "/data/series-zoe"`; rename docstring to "/data/<name>". Run → FAIL.
- [ ] Change generator: `savePath=f"/data/{c.name}"`. Fix the "Pitfall 3" docstring/comment (now: qBit `/data/<name>` == Sonarr `/data/torrents/<name>` via mount offset; RPM bridges). Run → PASS.

### Task 2: Fix qbit_manage `root_dir`/`recycle_bin` (intent generator)

**Files:**
- Modify: `tools/arrconf/arrconf/generators/intent.py:97,136-142`
- Test: existing `test_generate_cmd.py` / `test_config.py` referencing qbit_manage output

- [ ] `root_dir: /data`, `recycle_bin: /data/.RecycleBin`; update comment (line 97 `/data/torrents/<name>` → `/data/<name>`). The `cat:` mapping at line 148 reads `cat.savePath` → auto-correct after Task 1.
- [ ] Update any test asserting `root_dir: /data/torrents` or qbit_manage cat `/data/torrents/<name>`.

### Task 3: Fix audit.py internal contradiction

**Files:**
- Modify: `tools/arrconf/arrconf/audit.py:345,701`
- Test: `tools/arrconf/tests/test_audit.py` (category-drift expected + headers)

- [ ] `expected = f"/data/{cat_name}"`; header → `expected_savePath (/data/<name>)`. Update test expectations. Confirm legacy-detection tests (obsolete *names* like `films-anime`) still pass — those key on name, not prefix.

### Task 4: Regenerate config + co-bump + green suite

- [ ] `cd tools/arrconf && uv run python -m arrconf generate` (or the documented regen) → regenerates `charts/arr-stack/files/qbit_manage/config.yml` + `arrconf.yml`. Verify cat: now `/data/<name>` and root_dir `/data`.
- [ ] Triad: `uv run ruff format --check . && uv run ruff check . && uv run mypy arrconf` → green.
- [ ] `uv run pytest` → full suite green.
- [ ] Co-bump `charts/arr-stack/values.yaml#arrconf.image.tag` to the predicted next chart tag (verify last tag first).
- [ ] Commit.

### Task 5: Ship + live migration

- [ ] Merge → push → wait for chart-lint `tag` job → verify image build (per image-tag memory: image semver == chart git tag).
- [ ] Bump my-kluster `targetRevision`, ArgoCD sync, run arrconf apply job → exit 0; verify qBit category savePaths now `/data/<name>`.
- [ ] Enumerate torrents with save_path under `/data/torrents/<name>`; qBit Set-location each → `/data/<name>` (preserves seeding + moves files).
- [ ] Trigger Sonarr `RescanSeries` / Radarr `RescanMovie`; confirm From.S01 imports.
