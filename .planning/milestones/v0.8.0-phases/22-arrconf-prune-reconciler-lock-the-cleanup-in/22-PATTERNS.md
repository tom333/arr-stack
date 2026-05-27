# Phase 22: arrconf prune reconciler — lock the cleanup in - Pattern Map

**Mapped:** 2026-05-27
**Files analyzed:** 7 new/modified files + 3 new test files
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `tools/arrconf/arrconf/differ.py` | utility (classifier engine) | transform | self (extend `reconcile()`) | exact — extend existing |
| `tools/arrconf/arrconf/reconcilers/sonarr.py` | reconciler | CRUD | self (lines 516-558) | exact — wire new prune path |
| `tools/arrconf/arrconf/reconcilers/radarr.py` | reconciler | CRUD | `reconcilers/sonarr.py` (mirror) | exact — mirror of sonarr |
| `tools/arrconf/arrconf/reconcilers/qbittorrent.py` | reconciler | CRUD | self (lines 161-200) | exact — extend `PRUNE_PROTECTED` override |
| `tools/arrconf/arrconf/config.py` | config/validation | transform | self (`load_config()` lines 664-681) | exact — extend post-instantiation guard |
| `tools/arrconf/tests/test_differ.py` | test | transform | self (lines 46-113) | exact — add untagged-prune cases |
| `tools/arrconf/tests/test_reconcilers_sonarr.py` | test | CRUD | self (lines 325-447) | exact — prune/delete pattern |
| `tools/arrconf/tests/test_reconcilers_radarr.py` | test | CRUD | `test_reconcilers_sonarr.py` mirror | exact — mirror pattern |
| `tools/arrconf/tests/test_reconcilers_qbittorrent.py` | test | CRUD | self (lines 375-407) | exact — prune override pattern |
| `tools/arrconf/tests/test_config_validation.py` | test | transform | self (lines 18-49) | exact — pydantic guard pattern |
| `charts/arr-stack/values.yaml:451` | config | — | self | exact — co-bump pin |

---

## Pattern Assignments

### `tools/arrconf/arrconf/differ.py` — extend `reconcile()`

**Analog:** self (lines 250-299)

**Problem (D-02/D-04):** The current `reconcile()` classifier at line 291-294 gates ALL deletes on `managed_tag_id in cur_tags`. Resources without tags (root_folders, tag resources) and the untagged legacy catch-all DC can never reach `Action.DELETE` through this path — they always land on `PRUNE_PROTECTED`. D-04 requires a deliberate bypass for untaggable resource categories.

**Current classifier body that must be worked around** (lines 284-298):
```python
for name, cur in by_name_current.items():
    if name in by_name_desired:
        continue
    if not prune:
        plan.append(PlannedAction(Action.PRUNE_SKIP, name, cur, None, []))
        log.warning("prune_skip", name=name, hint="not in YAML, prune=False (default)")
        continue
    cur_tags = list(getattr(cur, "tags", None) or [])
    if managed_tag_id is None or managed_tag_id not in cur_tags:
        plan.append(PlannedAction(Action.PRUNE_PROTECTED, name, cur, None, []))
        log.warning("prune_protected", name=name, hint="missing arrconf-managed tag")
    else:
        plan.append(PlannedAction(Action.DELETE, name, cur, None, []))
        log.info("plan_action", action="delete", name=name)
```

**Resolution approach (D-04):** Add a new boolean parameter `force_prune: bool = False` to `reconcile()`. When `force_prune=True` AND `prune=True`, skip the managed-tag gate entirely and classify directly as `Action.DELETE`. This is the "allowlist-is-the-trust-boundary" path. The `arrconf-managed` **tag itself** is never passed to this path (its protection is handled by `_ensure_managed_tag` — it is never in `by_name_current` for the tags reconcile call because it is matched in desired).

**Signature extension pattern** (copy from existing signature, lines 250-257):
```python
def reconcile[T: BaseModel](
    current: list[T],
    desired: list[T],
    *,
    match_key: str = "name",
    prune: bool = False,
    managed_tag_id: int | None = None,
    force_prune: bool = False,   # NEW — D-04 untagged prune path
) -> list[PlannedAction[T]]:
```

**New branch to insert** (after existing `PRUNE_PROTECTED` check):
```python
    cur_tags = list(getattr(cur, "tags", None) or [])
    if managed_tag_id is None or managed_tag_id not in cur_tags:
        if force_prune:
            # D-04: allowlist-boundary prune — no managed-tag check required.
            # Used for untaggable resources (root_folders, tags) and explicit
            # legacy-artifact cleanup (catch-all DC id=1). Caller is responsible
            # for constraining the desired set to the allowlist (generator output).
            plan.append(PlannedAction(Action.DELETE, name, cur, None, []))
            log.info("plan_action", action="delete", name=name,
                     hint="force_prune=True, no managed-tag check")
        else:
            plan.append(PlannedAction(Action.PRUNE_PROTECTED, name, cur, None, []))
            log.warning("prune_protected", name=name, hint="missing arrconf-managed tag")
    else:
        plan.append(PlannedAction(Action.DELETE, name, cur, None, []))
        log.info("plan_action", action="delete", name=name)
```

---

### `tools/arrconf/arrconf/reconcilers/sonarr.py` — wire prune on root_folders, tags, DCs

**Analog:** self — the existing `_reconcile_list_resource()` call at lines 516-528 (root_folders) and `_reconcile_tags()` at lines 271-309, and the manual `reconcile()` call at lines 550-556 (download_clients).

**Root folders wiring** (current pattern, lines 516-528 — change `managed_tag_id` + add `force_prune`):
```python
# Step 4: Root folders (match by PATH — Pitfall 1; no managed tag).
log.info("step_begin", step="root_folders", step_index=4)
actions_taken += _reconcile_list_resource(
    client,
    ROOT_FOLDER_PATH,
    client.get(ROOT_FOLDER_PATH),
    RootFolder,
    derived.root_folders,
    match_key="path",
    prune=instance.root_folders.prune,
    managed_tag_id=None,
    dry_run=dry_run,
)
```
Phase 22 change: pass `force_prune=instance.root_folders.prune` (root folders are untaggable — the allowlist IS the safety boundary per D-04).

**Tags wiring** (`_reconcile_tags()`, lines 292-304 — the `managed_tag_id=None` call to `_reconcile_list_resource`):
```python
_reconcile_list_resource(
    client,
    TAG_PATH,
    raw_current,
    Tag,
    desired_tags,
    match_key="label",
    prune=section.prune,
    managed_tag_id=None,
    dry_run=dry_run,
)
```
Phase 22 change: pass `force_prune=section.prune` here too. The `arrconf-managed` tag is protected because it IS in `desired_tags` (it was added by `_ensure_managed_tag` and the generator always includes it via the categories list) — it will match in `by_name_desired` and never reach the prune branch.

**Download clients wiring** (current pattern, lines 550-556 — the catch-all legacy DC has no `arrconf-managed` tag):
```python
plan = reconcile(
    current=current_dcs,
    desired=desired_dcs,
    match_key="name",
    prune=instance.download_clients.prune,
    managed_tag_id=managed_tag_id,
)
```
Phase 22 change: This is the correct wiring for managed DCs. The legacy catch-all `qBittorrent` (id=1, no tags) is NOT in `desired_dcs` and has no `arrconf-managed` tag — it currently lands on `PRUNE_PROTECTED`. To prune it, callers must either: (a) pass `force_prune=instance.download_clients.prune` alongside the existing `managed_tag_id` (new `force_prune` path fires when managed-tag check fails), or (b) keep the managed-tag path for managed DCs and let `force_prune` handle untagged orphans. Option (a) is correct: both tagged (managed) and untagged (legacy) DCs are prunable when `prune=True`.

**`_reconcile_list_resource()` signature extension** (lines 172-205 — add `force_prune` passthrough):
```python
def _reconcile_list_resource(
    client: SonarrClient,
    path: str,
    raw_current: list[dict[str, Any]],
    model_cls: type[BaseModel],
    desired_items: list[Any],
    match_key: str,
    prune: bool,
    managed_tag_id: int | None,
    dry_run: bool,
    force_prune: bool = False,   # NEW — passthrough to reconcile()
) -> list[str]:
    current = [model_cls.model_validate(x) for x in raw_current]
    plan = reconcile(
        current=current,
        desired=desired_items,
        match_key=match_key,
        prune=prune,
        managed_tag_id=managed_tag_id,
        force_prune=force_prune,   # NEW
    )
    return _execute(client, path, plan, dry_run)
```

---

### `tools/arrconf/arrconf/reconcilers/radarr.py` — mirror of sonarr.py

**Analog:** `reconcilers/sonarr.py` — exact structural mirror.

Radarr's `_reconcile_list_resource()` (lines ~172-205) and root_folder step (~512-520) and `_reconcile_tags()` (~271-309) follow the same pattern as Sonarr. Apply identical `force_prune` wiring. The radarr file's `ROOT_FOLDER_PATH = "/rootfolder"` at line 89 and `TAG_PATH = "/tag"` are identical.

**Radarr root_folders step** (lines ~512-522):
```python
# Step 4: Root folders (match by PATH — Pitfall 1; no managed tag).
log.info("step_begin", step="root_folders", step_index=4)
actions_taken += _reconcile_list_resource(
    client,
    ROOT_FOLDER_PATH,
    client.get(ROOT_FOLDER_PATH),
    RootFolder,
    derived.root_folders,
    match_key="path",
    prune=instance.root_folders.prune,
    managed_tag_id=None,
    dry_run=dry_run,
    force_prune=instance.root_folders.prune,  # NEW
)
```

---

### `tools/arrconf/arrconf/reconcilers/qbittorrent.py` — PRUNE_PROTECTED override for catch-all DC

**Analog:** self — the `PRUNE_PROTECTED` override block at lines 183-200.

**Current PRUNE_PROTECTED override** (lines 183-200 — the exact pattern to reuse for the legacy catch-all DC deletion):
```python
elif p.action == Action.PRUNE_PROTECTED:
    # qBit categories have no managed-tag concept (R-05), so differ.reconcile()
    # emits PRUNE_PROTECTED (not DELETE) when managed_tag_id=None + prune=True.
    # We override here: if the operator explicitly set prune=True, execute the
    # delete (no tag guard needed — the operator is the trust boundary).
    assert p.current is not None
    if prune:
        log.info("plan_action", action="delete", name=p.name)
        if dry_run:
            log.info("dry_run_skip", action="delete", name=p.name)
        else:
            client.post_form(
                REMOVE_CATEGORIES_PATH,
                data={"categories": p.current.name},
            )
            actions_taken.append(f"delete:{p.name}")
    else:
        log.info("prune_skip", resource="qbit_category", name=p.name)
```

**Phase 22 usage:** The catch-all DC `qBittorrent` (id=1, no `arrconf-managed` tag) is a Sonarr/Radarr download-client resource, NOT a qBit category. It lives in Sonarr and Radarr's `/api/v3/downloadclient` endpoint. The qBit reconciler itself has no DC concept to extend. The `force_prune` path added to `differ.reconcile()` is the mechanism that enables the legacy catch-all DC deletion in **Sonarr and Radarr reconcilers** when `instance.download_clients.prune=True`.

However, if `force_prune` is wired into the `differ.reconcile()` call for download_clients (as described above under sonarr.py), then the qBittorrent reconciler requires no changes for the DC prune — the DC deletion happens entirely in the *arr reconcilers. The qBit reconciler only needs changes if there is a qBit-side artifact to clean. Per D-01, the catch-all to prune is in Sonarr/Radarr, not in qBit itself.

**Role of qbit reconciler in Phase 22:** No code changes required unless a "qBittorrent" download client entry also exists in the qBit category list (it does not — qBit categories are separate from the *arr download client records). The qBit reconciler is pattern-only reference for the `PRUNE_PROTECTED` override idiom.

---

### `tools/arrconf/arrconf/config.py` — D-08 legacy-path guard in `load_config()`

**Analog:** self — `load_config()` at lines 664-681, plus `test_config_validation.py` as the pattern for the existing structural guard.

**Current `load_config()` body** (lines 664-681 — the D-08 hook lives HERE, after `model_validate`):
```python
def load_config(path: Path) -> RootConfig:
    """Load and validate a YAML config file.

    Raises ``ConfigError`` (mapped to CLI exit code 2) for missing file,
    YAML parse failure, or pydantic validation failure (D-13 / D-22).
    """
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    yaml = YAML(typ="safe")
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.load(f) or {}
    except Exception as e:
        raise ConfigError(f"YAML parse error in {path}: {e}") from e
    try:
        return RootConfig.model_validate(raw)
    except ValidationError as e:
        raise ConfigError(f"Config validation error in {path}: {e}") from e
```

**D-08 guard insertion point:** After `RootConfig.model_validate(raw)` succeeds, insert a semantic check against the 4 legacy names before returning:

```python
    try:
        cfg = RootConfig.model_validate(raw)
    except ValidationError as e:
        raise ConfigError(f"Config validation error in {path}: {e}") from e
    # D-08 / Phase 22: deny legacy bucket names in categories[].name
    _check_no_legacy_categories(cfg, path)
    return cfg
```

**New helper** (immediately above `load_config`, following the private-helper naming convention `_` prefix):
```python
_LEGACY_CATEGORY_NAMES: frozenset[str] = frozenset({
    "films-anime", "films-family", "anime", "family"
})

def _check_no_legacy_categories(cfg: RootConfig, path: Path) -> None:
    """Deny legacy v0.2.0 bucket names in categories[].name (D-07/D-08).

    Raises ConfigError (exit 2) naming the offending category.
    ``films`` and ``series`` are valid default Categories — NOT denied.
    """
    for cat in cfg.categories:
        if cat.name in _LEGACY_CATEGORY_NAMES:
            raise ConfigError(
                f"Config validation error in {path}: "
                f"legacy category name {cat.name!r} is not allowed "
                f"(v0.2.0 bucket — remove from categories[] or rename). "
                f"Denied names: {sorted(_LEGACY_CATEGORY_NAMES)}"
            )
```

**Import already available:** `ConfigError` is imported at line 22 of config.py. `RootConfig` is defined in the same file. No new imports needed.

---

### `tools/arrconf/arrconf/generators/categories.py` — allowlist source (read-only reference)

**Analog:** self — `generate_sonarr_resources()` lines 135-164, `generate_radarr_resources()` lines 167-196.

**Allowlist derivation pattern** (D-03): The desired set for root_folders/tags/DCs is exactly the generator output. In the reconcilers, `derived.root_folders` (a `list[RootFolder]`) and `derived.tags` (a `list[TagItem]`) already represent the allowlist. The `match_key="path"` comparison for root_folders and `match_key="label"` for tags means any cluster entry whose key is NOT in the generated list is prunable when `force_prune=True`.

```python
# Sonarr: series categories → 5 root_folders
root_folders=[RootFolder(path=c.base_path) for c in series],
# series Categories base_path = /media/{name}, e.g. /media/series, /media/series-emilie

# Tags: one per category name
tags=[TagItem(label=c.name) for c in series],
# e.g. "series", "series-emilie", "series-thomas", "series-garcons", "series-zoe"
```

The 4 paths to prune (D-05):
- Radarr: `/media/films-anime`, `/media/films-family`
- Sonarr: `/media/anime`, `/media/family`

These are NOT in `generate_sonarr_resources()` or `generate_radarr_resources()` output because `films-anime`, `films-family`, `anime`, `family` are not declared in `categories[]`. The generator output is the safety boundary.

---

## New Test Files

### `tools/arrconf/tests/test_differ.py` — add `force_prune` cases

**Analog:** self (lines 46-113). The 6 existing test cases cover the current 6 outcomes. Add 2 new cases for the `force_prune` path.

**Pattern to copy** (existing prune tests, lines 51-60):
```python
def test_prune_protected_when_no_managed_tag() -> None:
    cur = _dc("orphan", tags=[5])
    plan = reconcile(current=[cur], desired=[], prune=True, managed_tag_id=99)
    assert plan[0].action == Action.PRUNE_PROTECTED


def test_prune_executed_when_tag_present() -> None:
    cur = _dc("orphan", tags=[99])
    plan = reconcile(current=[cur], desired=[], prune=True, managed_tag_id=99)
    assert plan[0].action == Action.DELETE
```

**New cases to add** (follow the same `_dc()` builder pattern):
```python
def test_force_prune_deletes_untagged_resource() -> None:
    """D-04: force_prune=True bypasses managed-tag check → DELETE even with no tag."""
    cur = _dc("legacy-qbit", tags=[])   # no managed tag
    plan = reconcile(current=[cur], desired=[], prune=True, managed_tag_id=99,
                     force_prune=True)
    assert plan[0].action == Action.DELETE


def test_force_prune_false_still_protects_untagged() -> None:
    """D-04: force_prune=False (default) preserves existing PRUNE_PROTECTED behaviour."""
    cur = _dc("legacy-qbit", tags=[])
    plan = reconcile(current=[cur], desired=[], prune=True, managed_tag_id=99,
                     force_prune=False)
    assert plan[0].action == Action.PRUNE_PROTECTED


def test_force_prune_requires_prune_true() -> None:
    """force_prune without prune=True is not reachable; prune=False → PRUNE_SKIP."""
    cur = _dc("legacy-qbit", tags=[])
    plan = reconcile(current=[cur], desired=[], prune=False, force_prune=True)
    assert plan[0].action == Action.PRUNE_SKIP
```

---

### `tools/arrconf/tests/test_reconcilers_sonarr.py` — root_folder prune + tag prune + catch-all DC prune

**Analog:** self — the prune block at lines 325-447 (DC prune tests) and the root_folder tests at lines 781-846.

**Delete pattern to copy** (lines 404-447 — the gold standard for prune+delete with respx):
```python
@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_prune_executes_with_managed_tag(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    orphan_managed = [{
        "id": 99, "name": "old-qbit", "enable": True, "protocol": "torrent",
        "priority": 1, "implementation": "QBittorrent",
        "configContract": "QBittorrentSettings", "fields": [],
        "tags": [1],   # managed tag id from fixture
        "removeCompletedDownloads": True, "removeFailedDownloads": True,
    }]
    _mock_base_gets(respx_mock, sonarr_tag_managed_fixture, downloadclients=orphan_managed)
    delete_route = respx_mock.delete(
        url__regex=r"^http://sonarr\.test/api/v3/downloadclient/\d+$"
    ).mock(return_value=httpx.Response(204))

    instance = SonarrInstance(
        base_url="http://sonarr.test",
        download_clients=DownloadClientsSection(prune=True),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(client, instance, SonarrDerived(...), dry_run=False)

    assert delete_route.call_count == 1
    assert any(p.action == Action.DELETE and p.name == "old-qbit" for p in result.plan)
```

**New tests to add** (following this exact pattern):

1. `test_root_folder_prune_deletes_legacy_path` — cluster has `/media/anime` (legacy), desired has only 5 Category paths. With `root_folders=RootFoldersSection(prune=True)`, expect `DELETE /rootfolder/<id>`.

2. `test_root_folder_prune_false_skips_legacy` — same setup but `prune=False` → 0 DELETE, `PRUNE_SKIP`.

3. `test_tag_prune_deletes_legacy_tag` — cluster has tags `["tv", "anime", "arrconf-managed"]`, desired = `["tv", "arrconf-managed"]`. With `tags=TagsSection(prune=True)` → DELETE `"anime"`.

4. `test_catch_all_dc_prune_deletes_untagged` — cluster DC `"qBittorrent"` (id=1, `tags=[]`), desired empty. With `download_clients=DownloadClientsSection(prune=True)` → DELETE issued (force_prune path). This is the key Phase 22 SC#4 test.

5. `test_catch_all_dc_prune_false_protects_untagged` — same but `prune=False` → PRUNE_SKIP (existing behaviour, regression guard).

**Mock pattern for root_folder DELETE** (follow lines 787-809):
```python
delete_rf = respx_mock.delete(
    url__regex=r"^http://sonarr\.test/api/v3/rootfolder/\d+$"
).mock(return_value=httpx.Response(200))
```

**Mock pattern for tag DELETE**:
```python
delete_tag = respx_mock.delete(
    url__regex=r"^http://sonarr\.test/api/v3/tag/\d+$"
).mock(return_value=httpx.Response(200))
```

---

### `tools/arrconf/tests/test_reconcilers_radarr.py` — mirror of sonarr prune tests

**Analog:** self + `test_reconcilers_sonarr.py`. Use `_mock_radarr_gets()` (lines 61-94) with `rootfolders=` and `tag=` kwargs. The 4 radarr-specific legacy paths are `/media/films-anime` and `/media/films-family`.

**Respx base URL:** `@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)` (RADARR_BASE = "http://radarr.test").

**New tests (mirror sonarr set):**
1. `test_root_folder_prune_deletes_legacy_films_anime`
2. `test_root_folder_prune_false_skips_legacy`
3. `test_tag_prune_deletes_legacy_films_family_tag`
4. `test_catch_all_dc_prune_deletes_untagged` (same DC scenario, radarr endpoint)

---

### `tools/arrconf/tests/test_config_validation.py` — D-08 legacy-name guard

**Analog:** self — `test_load_config_rejects_legacy_items_field()` (lines 18-49).

**Pattern to copy exactly** (this is the SC#3 test):
```python
def test_load_config_rejects_legacy_items_field() -> None:
    legacy_shape = {"sonarr": {"main": {"base_url": "...", "tags": {"prune": False, "items": [...]}}}}
    with pytest.raises(ValidationError) as exc_info:
        RootConfig.model_validate(legacy_shape)
    errors = exc_info.value.errors()
    extra_forbidden = [e for e in errors if e["type"] == "extra_forbidden"]
    assert extra_forbidden, ...
```

**New test** (calls `load_config()` with a temp file, asserts `ConfigError` + exit-2 signal):
```python
def test_load_config_rejects_legacy_category_name(tmp_path: pytest.TempPathFixture) -> None:
    """SC#3: synthetic config with films-family category → ConfigError (exit 2)."""
    cfg_file = tmp_path / "arrconf.yml"
    cfg_file.write_text(
        "categories:\n"
        "  - name: films-family\n"
        "    kind: movies\n"
        "    display: Films Family\n"
    )
    with pytest.raises(ConfigError) as exc_info:
        load_config(cfg_file)
    assert "films-family" in str(exc_info.value)
```

Import pattern (copy from top of `test_config_validation.py`):
```python
from arrconf.config import RootConfig, load_config
from arrconf.exceptions import ConfigError
```

---

## Shared Patterns

### Prune + dry_run guard (all reconcilers)
**Source:** `tools/arrconf/arrconf/reconcilers/sonarr.py` `_execute()` lines 141-145
**Apply to:** Every new DELETE path in Phase 22
```python
if p.action in (Action.NO_OP, Action.PRUNE_SKIP, Action.PRUNE_PROTECTED):
    continue
if dry_run:
    log.info("dry_run_skip", action=p.action.value, name=p.name)
    continue
# ... actual DELETE
```

### ConfigError exit-2 pattern
**Source:** `tools/arrconf/arrconf/config.py:671` + `tools/arrconf/arrconf/exceptions.py:20-21`
**Apply to:** D-08 guard in `load_config()`
```python
raise ConfigError(f"Config validation error in {path}: <descriptive message>")
```
The CLI maps `ConfigError` to exit code 2 (see `__main__.py`). No new exception class needed.

### structlog event naming
**Source:** `differ.py:294-296` and `sonarr.py:143-145`
**Apply to:** All new log events in Phase 22
```python
log.warning("prune_protected", name=name, hint="missing arrconf-managed tag")  # warning for protected
log.info("plan_action", action="delete", name=name, hint="force_prune=True, ...")  # info for planned
log.info("dry_run_skip", action="delete", name=p.name)  # info for dry-run suppressed
```

### Test fixture inline-dict pattern (no JSON file for Phase 22 prune cases)
**Source:** `test_reconcilers_sonarr.py` lines 363-378 (inline orphan fixture dict)
**Apply to:** All Phase 22 prune test cases — define orphan resources as inline dicts, not fixture files, since they are synthetic legacy scenarios with no cluster-snapshot basis.

---

## No Analog Found

None — all Phase 22 file modifications have close analogs in the codebase.

---

## Key Code Constraint: `arrconf-managed` tag protection invariant

The `arrconf-managed` tag (label `"arrconf-managed"`) MUST never be pruned. The protection works by ensuring it is always present in `desired_tags` when `_reconcile_tags()` is called:

- `_ensure_managed_tag()` (sonarr.py line 93) creates/finds the tag and returns its id.
- The tag label `"arrconf-managed"` is NOT generated by `generate_sonarr_resources()` — it is separate from Category-derived tags.
- However, since it lives in the same `/tag` endpoint, when tags are pruned the `desired_tags` list passed to `_reconcile_tags()` must include `TagItem(label="arrconf-managed")` to protect it.

**Resolution:** In `_reconcile_tags()`, after the generator produces `desired_tags`, prepend `TagItem(label=MANAGED_TAG_LABEL)` if not already present:
```python
# Protect arrconf-managed from prune: it is not a Category-derived tag
# but lives in the same /tag list that prune will sweep.
if not any(t.label == MANAGED_TAG_LABEL for t in desired_tags):
    desired_tags = [TagItem(label=MANAGED_TAG_LABEL)] + desired_tags
```
This is the correct injection point — analogous to `_ensure_managed_tag_in_desired()` (sonarr.py line 114) for DCs.

---

## Chart Co-bump

**Source:** `charts/arr-stack/values.yaml:449-451`
**Change:** `tag: "0.14.1"` → `tag: "0.15.0"` in the same commit as the Python code.
```yaml
          image:
            # renovate: image=ghcr.io/tom333/arr-stack-arrconf
            repository: ghcr.io/tom333/arr-stack-arrconf
            tag: "0.15.0"   # ← Phase 22 co-bump (0.14.1 → 0.15.0)
```
The `# renovate: image=...` annotation at line 449 MUST be preserved verbatim (CLAUDE.md §"Annotations Renovate").

---

## Metadata

**Analog search scope:** `tools/arrconf/arrconf/` (differ, reconcilers, config, generators, exceptions), `tools/arrconf/tests/` (all test files)
**Files scanned:** 12 source files, 10 test files
**Pattern extraction date:** 2026-05-27
