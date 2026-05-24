---
phase: 18-qbit-post-credentials-fallback
plan: A
type: execute
wave: 1
depends_on: []
files_modified:
  - tools/arrconf/arrconf/reconcilers/_shared.py
  - tools/arrconf/arrconf/reconcilers/sonarr.py
  - tools/arrconf/arrconf/reconcilers/radarr.py
  - tools/arrconf/tests/test_qbit_credentials_env_fallback.py
  - charts/arr-stack/values.yaml
  - .planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md
autonomous: true
requirements:
  - REQ-qbit-post-credentials
tags:
  - reconciler
  - qbittorrent
  - download_clients
  - env-injection

must_haves:
  truths:
    - "When YAML username/password fields are empty for a qBit download_client, the reconciler injects os.environ['QBT_USER'] / os.environ['QBT_PASS'] before the POST/PUT body is built (SC#1)"
    - "When YAML fields are explicit (non-empty), env values are ignored and YAML wins verbatim (SC#1 + SC#2 case b)"
    - "When YAML field is empty AND the corresponding env var is unset/empty, the reconciler raises ConfigError naming the offending download_client entry — fail-fast, exit code 2 (SC#1)"
    - "Helper _resolve_qbit_credentials_from_env() is called from BOTH sonarr.py and radarr.py download_clients steps (D-18-SCOPE-01)"
    - "Respx unit tests cover the 3 mandated cases (a) YAML empty + env set, (b) YAML explicit (env ignored), (c) partial (YAML username + env password) plus 1 ConfigError case plus 1 idempotence case = 5 tests minimum (SC#2 + SC#3)"
    - "Second arrconf apply emits 0 plan_action on download_clients with env-injected creds (SC#3 — acquired by construction via existing merge_fields_for_put at differ.py:148, verified by an explicit respx test)"
    - "charts/arr-stack/values.yaml#arrconf.image.tag bumped 0.10.0 → 0.10.1 in the same commit as the Python code (D-18-CHART-BUMP-01, SC#4)"
    - "# renovate: image=ghcr.io/tom333/arr-stack-arrconf annotation preserved verbatim immediately above repository: line (SC#4)"
    - "Triade Python green from tools/arrconf/: uv run ruff format --check . && uv run ruff check . && uv run mypy . && uv run pytest --cov-fail-under=70 (CLAUDE.md mandatory gate)"
    - "18-HUMAN-UAT.md documents the 5 operator scenarios from CONTEXT.md (SC#5)"
  artifacts:
    - path: "tools/arrconf/arrconf/reconcilers/_shared.py"
      provides: "Public helper _resolve_qbit_credentials_from_env(dcs: list[DownloadClient]) -> list[DownloadClient]"
      contains: "def _resolve_qbit_credentials_from_env"
    - path: "tools/arrconf/arrconf/reconcilers/sonarr.py"
      provides: "Call site wired between _resolve_download_client_tag_labels and reconcile() in the download_clients step (line ~545)"
      contains: "_resolve_qbit_credentials_from_env"
    - path: "tools/arrconf/arrconf/reconcilers/radarr.py"
      provides: "Symmetric call site in the download_clients step (line ~540)"
      contains: "_resolve_qbit_credentials_from_env"
    - path: "tools/arrconf/tests/test_qbit_credentials_env_fallback.py"
      provides: "5 unit tests covering SC#2 (3 cases) + ConfigError + SC#3 idempotence"
      contains: "test_yaml_empty_env_set_uses_env_values"
    - path: "charts/arr-stack/values.yaml"
      provides: "arrconf.image.tag co-bump 0.10.0 → 0.10.1 (D-18-CHART-BUMP-01)"
      contains: 'tag: "0.10.1"'
    - path: ".planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md"
      provides: "Operator UAT runbook for SC#5 — strip qBit creds, ArgoCD sync, kubectl logs confirm 0 drift"
  key_links:
    - from: "tools/arrconf/arrconf/reconcilers/sonarr.py"
      to: "tools/arrconf/arrconf/reconcilers/_shared.py::_resolve_qbit_credentials_from_env"
      via: "function call between label resolution and reconcile() — runs before differ sees the DCs"
      pattern: "_resolve_qbit_credentials_from_env\\("
    - from: "tools/arrconf/arrconf/reconcilers/radarr.py"
      to: "tools/arrconf/arrconf/reconcilers/_shared.py::_resolve_qbit_credentials_from_env"
      via: "function call between label resolution and reconcile()"
      pattern: "_resolve_qbit_credentials_from_env\\("
    - from: "tools/arrconf/arrconf/reconcilers/_shared.py"
      to: "os.environ['QBT_USER'] / os.environ['QBT_PASS']"
      via: "os.environ.get() called per-invocation (no module-level cache — tests need monkeypatch to survive)"
      pattern: "os\\.environ"
    - from: "tools/arrconf/arrconf/reconcilers/_shared.py"
      to: "arrconf.exceptions.ConfigError"
      via: "raise ConfigError(...) when YAML field empty AND env var unset/empty"
      pattern: "raise ConfigError"
    - from: "charts/arr-stack/values.yaml"
      to: "ghcr.io/tom333/arr-stack-arrconf:0.10.1"
      via: "co-bump anchors next CronJob image pull to the rebuilt image including this fix"
      pattern: 'tag: "0\\.10\\.1"'
---

<objective>
Implement the qBit POST credentials env-injection fallback so that empty `username` / `password` fields in qBit `download_clients` (currently produced as literal `""` by the pure Categories generator) are substituted with `QBT_USER` / `QBT_PASS` from the environment at reconcile time — for both Sonarr and Radarr — with fail-fast `ConfigError` when both YAML and env are empty. Idempotence is acquired by construction via the existing `differ.merge_fields_for_put` (Phase 2.1 / D-02.2-AUTH-REGRESSION) and confirmed by an explicit respx test.

Purpose: Close REQ-qbit-post-credentials and the v0.5.0 milestone. Today, after `arrconf apply` creates a qBit DC via POST, the Sonarr/Radarr "Test" button fails with HTTP 401 because the POST body carries `username: ""` / `password: ""`. Operator workaround = enter creds in the UI manually → breaks "fully-as-code". Phase 18 fix is ~50 LOC + 5 tests + chart-pin co-bump.

Output:
- 1 new helper in `_shared.py` (~30 LOC)
- 2 wired call sites in `sonarr.py` + `radarr.py` (~2 LOC each)
- 1 new test file with 5 respx tests
- 1 chart-pin co-bump `0.10.0 → 0.10.1`
- 1 `18-HUMAN-UAT.md` runbook
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/18-qbit-post-credentials-fallback/18-CONTEXT.md
@CLAUDE.md
@tools/arrconf/arrconf/reconcilers/_shared.py
@tools/arrconf/arrconf/reconcilers/sonarr.py
@tools/arrconf/arrconf/reconcilers/radarr.py
@tools/arrconf/arrconf/exceptions.py
@tools/arrconf/arrconf/resources/sonarr/download_client.py
@tools/arrconf/arrconf/differ.py
@tools/arrconf/arrconf/settings.py
@charts/arr-stack/values.yaml

<interfaces>
<!-- Key types and call signatures extracted from the codebase. -->
<!-- Executor MUST use these directly — no codebase exploration needed. -->

From tools/arrconf/arrconf/resources/sonarr/download_client.py:
```python
class FieldKV(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    value: Any | None = Field(default=None)
    # UI metadata excluded from diff (label, helpText, advanced, type, order,
    # privacy, selectOptions, isFloat, placeholder) — exclude=True

class DownloadClient(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str                       # matching key
    enable: bool = True
    protocol: Literal["torrent", "usenet"]
    priority: int = 1
    implementation: str
    configContract: str
    fields: list[FieldKV] = Field(default_factory=list)  # <-- mutate THIS list
    tags: list[int] = Field(default_factory=list)
    tag_labels: list[str] = Field(default_factory=list, exclude=True)
    removeCompletedDownloads: bool = True
    removeFailedDownloads: bool = True
    id: int | None = Field(default=None, exclude=True)
    # ...
```

From tools/arrconf/arrconf/exceptions.py:
```python
class ConfigError(Exception):
    """YAML parsing or validation failed (CLI exit code 2)."""
```

From tools/arrconf/arrconf/reconcilers/_shared.py (the analog to mirror, lines 103-150):
```python
def _resolve_download_client_tag_labels(
    items: list[Any],
    all_tags: list[Tag],
    app_name: str = "Sonarr/Radarr",
) -> list[Any]:
    """Resolve label-based tags ... Returns new DownloadClient instances
    (immutable copy via model_copy) with resolved integer ids appended to
    the existing ``tags`` list."""
    # ...
    resolved = []
    for dc in items:
        # ...
        resolved.append(dc.model_copy(update={"tags": resolved_ids}))
    return resolved
```

From tools/arrconf/arrconf/reconcilers/sonarr.py (the inject point, lines 538-546):
```python
# Step 6: Download clients (original Phase 1 — managed-tag-stamped + label-resolved).
# MUST run AFTER tags (step 2) so resolved IDs exist.
log.info("step_begin", step="download_clients", step_index=6)
raw_current = client.get(DOWNLOAD_CLIENT_PATH)
current_dcs = [DownloadClient.model_validate(x) for x in raw_current]

# Resolve string tag labels → integer IDs using the post-reconcile all_tags list.
label_resolved = _resolve_download_client_tag_labels(derived.download_clients, all_tags)
desired_dcs = [_ensure_managed_tag_in_desired(dc, managed_tag_id) for dc in label_resolved]
```

From tools/arrconf/arrconf/reconcilers/radarr.py (the symmetric inject point, lines 533-543):
```python
log.info("step_begin", step="download_clients", step_index=6)
raw_current = client.get(DOWNLOAD_CLIENT_PATH)
current_dcs = [DownloadClient.model_validate(x) for x in raw_current]

# Resolve string tag labels → integer IDs using the post-reconcile all_tags list.
label_resolved = _resolve_download_client_tag_labels(
    derived.download_clients, all_tags, app_name="Radarr"
)
desired_dcs = [_ensure_managed_tag_in_desired(dc, managed_tag_id) for dc in label_resolved]
```

From tools/arrconf/arrconf/generators/categories.py (lines 80-95, where the empty strings ORIGINATE — DO NOT MODIFY):
```python
def _qbit_dc_fields_sonarr(category_name: str) -> list[FieldKV]:
    return [
        FieldKV(name="host", value=_QBIT_HOST),
        FieldKV(name="port", value=_QBIT_PORT),
        FieldKV(name="useSsl", value=False),
        FieldKV(name="urlBase", value=""),
        FieldKV(name="username", value=""),   # <-- empty by design
        FieldKV(name="password", value=""),   # <-- empty by design
        # ...
    ]
```

From charts/arr-stack/values.yaml (lines 447-452 — the co-bump target):
```yaml
        main:
          image:
            # renovate: image=ghcr.io/tom333/arr-stack-arrconf
            repository: ghcr.io/tom333/arr-stack-arrconf
            tag: "0.10.0"
            pullPolicy: IfNotPresent
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add _resolve_qbit_credentials_from_env() helper in _shared.py</name>
  <files>tools/arrconf/arrconf/reconcilers/_shared.py</files>
  <read_first>
    - tools/arrconf/arrconf/reconcilers/_shared.py (FULL FILE — you are appending to it; do NOT re-implement existing helpers)
    - tools/arrconf/arrconf/reconcilers/_shared.py:103-150 (the analog `_resolve_download_client_tag_labels` whose shape this new helper mirrors)
    - tools/arrconf/arrconf/exceptions.py (verify `ConfigError` import path: `from arrconf.exceptions import ConfigError`)
    - tools/arrconf/arrconf/resources/sonarr/download_client.py (verify FieldKV.value type is `Any | None` — substitution must be type-compatible)
    - tools/arrconf/arrconf/generators/categories.py:80-118 (see exactly where `username`/`password` empty strings originate so the helper's matching logic is unambiguous)
  </read_first>
  <behavior>
    - Test 1 (Task 3 implements; this task only asserts behavior shape):
      Given a DownloadClient with `fields=[FieldKV(name="username", value=""), FieldKV(name="password", value="")]`
      AND `os.environ["QBT_USER"]="qbituser"` AND `os.environ["QBT_PASS"]="qbitpass"`
      When `_resolve_qbit_credentials_from_env([dc])` is called
      Then the returned DC has `fields[name=username].value == "qbituser"` and `fields[name=password].value == "qbitpass"`
      AND the input `dc` instance is NOT mutated (returned via model_copy — symmetry with `_resolve_download_client_tag_labels`)
    - Test 2: Given `fields=[FieldKV(name="username", value="explicit-user"), FieldKV(name="password", value="explicit-pass")]` AND env set → returned DC has unchanged YAML values; env IGNORED.
    - Test 3 (partial): Given `fields=[FieldKV(name="username", value="explicit-user"), FieldKV(name="password", value="")]` AND `os.environ["QBT_PASS"]="from-env"` → returned DC has `username="explicit-user"` + `password="from-env"`.
    - Test 4 (ConfigError): Given `fields=[FieldKV(name="username", value=""), ...]` AND `QBT_USER` unset → `raise ConfigError("download_client 'qBittorrent-tv': username is empty in YAML AND QBT_USER env is unset/empty")` — exact format string per D-18-FAIL-FAST-01.
    - Test 5 (no-op): Given a DC whose `fields[]` contains NO `username` or `password` entry (e.g. a non-qBit DC like Transmission) → helper returns the DC unchanged (do not crash on missing field).
  </behavior>
  <action>
    Append (do not replace existing content) to `tools/arrconf/arrconf/reconcilers/_shared.py`:

    1. Add `import os` to the top-level imports block (after `from __future__ import annotations`, alongside existing `from typing` import).
    2. Update the existing import block `from arrconf.exceptions import ReconcileError` to ALSO import `ConfigError` — final line: `from arrconf.exceptions import ConfigError, ReconcileError`.
    3. Append at the end of the file the following helper (mirror `_resolve_download_client_tag_labels` shape — accept list, iterate, model_copy, return new list):

    ```python
    def _resolve_qbit_credentials_from_env(items: list[Any]) -> list[Any]:
        """Inject QBT_USER / QBT_PASS env vars into qBit download_client fields[].

        For each ``DownloadClient`` in ``items``, walk ``fields[]`` and for any entry
        named ``username`` or ``password`` whose ``value`` is ``""`` (or None), substitute
        the corresponding environment variable (``QBT_USER`` / ``QBT_PASS``). Explicit
        YAML values always win — env is consulted only when YAML field is empty/missing.

        Fails fast with ``ConfigError`` when YAML field is empty AND env var is unset or
        empty — operator gets a clear message naming the offending DC. Maps to CLI exit
        code 2 via ``__main__.py`` (D-18-FAIL-FAST-01).

        Reads ``os.environ`` directly on each call (NOT settings.py) so that pytest
        monkeypatch.setenv() interleaves with reconcile cycles in tests
        (D-18-INJECT-LOC-01 consequence).

        Returns new ``DownloadClient`` instances via ``model_copy`` — input list is not
        mutated. Symmetry with ``_resolve_download_client_tag_labels`` (line 103).

        Phase 18 (REQ-qbit-post-credentials). Sonarr and Radarr both call this helper
        from their respective ``download_clients`` reconcile step, BEFORE the
        differ-driven POST/PUT body composition (D-18-SCOPE-01).
        """
        env_user = os.environ.get("QBT_USER", "")
        env_pass = os.environ.get("QBT_PASS", "")

        resolved = []
        for dc in items:
            new_fields = []
            mutated = False
            for f in dc.fields:
                if f.name == "username":
                    current = f.value
                    if current is None or current == "":
                        if not env_user:
                            raise ConfigError(
                                f"download_client '{dc.name}': username is empty "
                                f"in YAML AND QBT_USER env is unset/empty"
                            )
                        new_fields.append(f.model_copy(update={"value": env_user}))
                        mutated = True
                        continue
                if f.name == "password":
                    current = f.value
                    if current is None or current == "":
                        if not env_pass:
                            raise ConfigError(
                                f"download_client '{dc.name}': password is empty "
                                f"in YAML AND QBT_PASS env is unset/empty"
                            )
                        new_fields.append(f.model_copy(update={"value": env_pass}))
                        mutated = True
                        continue
                new_fields.append(f)
            if mutated:
                resolved.append(dc.model_copy(update={"fields": new_fields}))
            else:
                resolved.append(dc)
        return resolved
    ```

    4. Do NOT remove or modify any existing helper in the file (`_reconcile_remote_path_mappings`, `_resolve_download_client_tag_labels`). Append-only.
    5. Do NOT add the helper to any `__all__` list (the file has none — the leading underscore signals package-private per the module docstring line 6-7).
  </action>
  <verify>
    <automated>cd /data/projets/perso/arr-stack/tools/arrconf &amp;&amp; grep -q "^def _resolve_qbit_credentials_from_env" arrconf/reconcilers/_shared.py &amp;&amp; grep -q "^import os$" arrconf/reconcilers/_shared.py &amp;&amp; grep -q "from arrconf.exceptions import ConfigError, ReconcileError" arrconf/reconcilers/_shared.py &amp;&amp; uv run ruff format --check arrconf/reconcilers/_shared.py &amp;&amp; uv run ruff check arrconf/reconcilers/_shared.py &amp;&amp; uv run mypy arrconf/reconcilers/_shared.py</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "^def _resolve_qbit_credentials_from_env" tools/arrconf/arrconf/reconcilers/_shared.py` returns `1`
    - `grep -c "^def _resolve_download_client_tag_labels" tools/arrconf/arrconf/reconcilers/_shared.py` returns `1` (existing helper preserved)
    - `grep -c "^def _reconcile_remote_path_mappings" tools/arrconf/arrconf/reconcilers/_shared.py` returns `1` (existing helper preserved)
    - `grep -q "import os" tools/arrconf/arrconf/reconcilers/_shared.py` succeeds (exit 0)
    - `grep -q "from arrconf.exceptions import ConfigError, ReconcileError" tools/arrconf/arrconf/reconcilers/_shared.py` succeeds
    - `grep -q "raise ConfigError" tools/arrconf/arrconf/reconcilers/_shared.py` succeeds (the fail-fast branch exists)
    - `grep -q "os.environ.get(\"QBT_USER\", \"\")" tools/arrconf/arrconf/reconcilers/_shared.py` succeeds
    - `grep -q "os.environ.get(\"QBT_PASS\", \"\")" tools/arrconf/arrconf/reconcilers/_shared.py` succeeds
    - `cd tools/arrconf && uv run ruff format --check arrconf/reconcilers/_shared.py` exits 0
    - `cd tools/arrconf && uv run ruff check arrconf/reconcilers/_shared.py` exits 0
    - `cd tools/arrconf && uv run mypy arrconf/reconcilers/_shared.py` exits 0
  </acceptance_criteria>
  <done>Helper function `_resolve_qbit_credentials_from_env` exists in `_shared.py`, mirrors `_resolve_download_client_tag_labels` shape (list-in/list-out via model_copy, no input mutation), raises `ConfigError` with the exact message format from D-18-FAIL-FAST-01 when YAML+env both empty, and the file passes the triad (format-check + lint + mypy).</done>
</task>

<task type="auto">
  <name>Task 2: Wire _resolve_qbit_credentials_from_env into sonarr.py and radarr.py download_clients steps</name>
  <files>tools/arrconf/arrconf/reconcilers/sonarr.py, tools/arrconf/arrconf/reconcilers/radarr.py</files>
  <read_first>
    - tools/arrconf/arrconf/reconcilers/sonarr.py:538-556 (the Step 6 download_clients block — inject point is between `label_resolved = ...` (line 545) and `desired_dcs = ...` (line 546))
    - tools/arrconf/arrconf/reconcilers/radarr.py:533-552 (the symmetric Step 6 block — inject point between `label_resolved = ...` (lines 540-542) and `desired_dcs = ...` (line 543))
    - tools/arrconf/arrconf/reconcilers/_shared.py (verify the helper exists from Task 1 and check existing imports to confirm `_resolve_download_client_tag_labels` is already imported — add `_resolve_qbit_credentials_from_env` to the same import statement)
  </read_first>
  <action>
    **Sonarr (`tools/arrconf/arrconf/reconcilers/sonarr.py`):**

    1. Locate the existing import of `_resolve_download_client_tag_labels` from `arrconf.reconcilers._shared`. Extend that import to also pull in the new helper. Example before/after (the exact import block name may differ — preserve existing import style and grouping):

       Before (representative):
       ```python
       from arrconf.reconcilers._shared import (
           _reconcile_remote_path_mappings,
           _resolve_download_client_tag_labels,
       )
       ```
       After:
       ```python
       from arrconf.reconcilers._shared import (
           _reconcile_remote_path_mappings,
           _resolve_download_client_tag_labels,
           _resolve_qbit_credentials_from_env,
       )
       ```

    2. In the Step 6 download_clients block (around line 545), add ONE line between the `label_resolved = ...` call and the `desired_dcs = ...` comprehension. Keep the line short — re-assign `label_resolved` so existing downstream variable name does not need to change:

       Before (line 545-546):
       ```python
       label_resolved = _resolve_download_client_tag_labels(derived.download_clients, all_tags)
       desired_dcs = [_ensure_managed_tag_in_desired(dc, managed_tag_id) for dc in label_resolved]
       ```
       After:
       ```python
       label_resolved = _resolve_download_client_tag_labels(derived.download_clients, all_tags)
       label_resolved = _resolve_qbit_credentials_from_env(label_resolved)
       desired_dcs = [_ensure_managed_tag_in_desired(dc, managed_tag_id) for dc in label_resolved]
       ```

    **Radarr (`tools/arrconf/arrconf/reconcilers/radarr.py`):**

    3. Locate the same import statement for `_resolve_download_client_tag_labels` (around line 71) and add `_resolve_qbit_credentials_from_env` to it (same shape as Sonarr edit above).

    4. In the Step 6 download_clients block (around line 540-543), add the symmetric line:

       Before (lines 540-543):
       ```python
       label_resolved = _resolve_download_client_tag_labels(
           derived.download_clients, all_tags, app_name="Radarr"
       )
       desired_dcs = [_ensure_managed_tag_in_desired(dc, managed_tag_id) for dc in label_resolved]
       ```
       After:
       ```python
       label_resolved = _resolve_download_client_tag_labels(
           derived.download_clients, all_tags, app_name="Radarr"
       )
       label_resolved = _resolve_qbit_credentials_from_env(label_resolved)
       desired_dcs = [_ensure_managed_tag_in_desired(dc, managed_tag_id) for dc in label_resolved]
       ```

    5. Do NOT modify the Prowlarr, Seerr, Jellyfin, qBittorrent (native), or other reconcilers — scope is locked to Sonarr + Radarr per D-18-SCOPE-01 (they're the only ones with qBit DC fields).
    6. Do NOT modify `__main__.py` — its existing Phase 5 gate (lines 274-281) covers the qBittorrent reconciler natif's env requirements; the new helper raises ConfigError independently and propagates up through normal exception handling.
  </action>
  <verify>
    <automated>cd /data/projets/perso/arr-stack/tools/arrconf &amp;&amp; grep -c "_resolve_qbit_credentials_from_env" arrconf/reconcilers/sonarr.py | grep -q "^2$" &amp;&amp; grep -c "_resolve_qbit_credentials_from_env" arrconf/reconcilers/radarr.py | grep -q "^2$" &amp;&amp; uv run ruff format --check arrconf/reconcilers/sonarr.py arrconf/reconcilers/radarr.py &amp;&amp; uv run ruff check arrconf/reconcilers/sonarr.py arrconf/reconcilers/radarr.py &amp;&amp; uv run mypy arrconf/reconcilers/sonarr.py arrconf/reconcilers/radarr.py</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "_resolve_qbit_credentials_from_env" tools/arrconf/arrconf/reconcilers/sonarr.py` returns `2` (1 import + 1 call site)
    - `grep -c "_resolve_qbit_credentials_from_env" tools/arrconf/arrconf/reconcilers/radarr.py` returns `2` (1 import + 1 call site)
    - In `sonarr.py`, the call to `_resolve_qbit_credentials_from_env` appears AFTER `_resolve_download_client_tag_labels` AND BEFORE `_ensure_managed_tag_in_desired` (verify via `grep -A 3 "_resolve_download_client_tag_labels(derived.download_clients, all_tags)" tools/arrconf/arrconf/reconcilers/sonarr.py | grep "_resolve_qbit_credentials_from_env"` succeeds)
    - In `radarr.py`, the call appears AFTER the multi-line `_resolve_download_client_tag_labels(...)` call AND BEFORE `_ensure_managed_tag_in_desired`
    - `grep -c "_resolve_qbit_credentials_from_env" tools/arrconf/arrconf/reconcilers/prowlarr.py 2>/dev/null` returns `0` (scope discipline — no leakage)
    - `grep -c "_resolve_qbit_credentials_from_env" tools/arrconf/arrconf/reconcilers/seerr.py 2>/dev/null` returns `0`
    - `grep -c "_resolve_qbit_credentials_from_env" tools/arrconf/arrconf/reconcilers/jellyfin.py 2>/dev/null` returns `0`
    - `grep -c "_resolve_qbit_credentials_from_env" tools/arrconf/arrconf/reconcilers/qbittorrent.py 2>/dev/null` returns `0`
    - `grep -c "_resolve_qbit_credentials_from_env" tools/arrconf/arrconf/__main__.py` returns `0` (no main.py change)
    - `grep -c "_resolve_qbit_credentials_from_env" tools/arrconf/arrconf/generators/categories.py` returns `0` (purity of generators preserved)
    - `grep -c "_resolve_qbit_credentials_from_env" tools/arrconf/arrconf/differ.py` returns `0`
    - `cd tools/arrconf && uv run ruff format --check arrconf/reconcilers/sonarr.py arrconf/reconcilers/radarr.py` exits 0
    - `cd tools/arrconf && uv run ruff check arrconf/reconcilers/sonarr.py arrconf/reconcilers/radarr.py` exits 0
    - `cd tools/arrconf && uv run mypy arrconf/reconcilers/sonarr.py arrconf/reconcilers/radarr.py` exits 0
  </acceptance_criteria>
  <done>Both `sonarr.py` and `radarr.py` import and call `_resolve_qbit_credentials_from_env` exactly once each, at the correct position between label resolution and managed-tag stamping. No other reconciler (Prowlarr/Seerr/Jellyfin/qBittorrent/generators/differ/main) references the new helper — scope discipline verified by grep counts. Triad green on both files.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Write 5 respx unit tests covering SC#2 (3 cases) + ConfigError + SC#3 idempotence</name>
  <files>tools/arrconf/tests/test_qbit_credentials_env_fallback.py</files>
  <read_first>
    - tools/arrconf/tests/test_reconcilers_sonarr.py (FULL FILE if &lt;500 lines, else read first 200 lines then use `grep -n "def test_\|respx_mock\|monkeypatch\|_mock_base_gets\|fixture" tools/arrconf/tests/test_reconcilers_sonarr.py | head -80` to understand existing test conventions, fixtures, and naming patterns)
    - tools/arrconf/tests/conftest.py (find existing fixtures — particularly `sonarr_tag_managed_fixture`, `radarr_tag_managed_fixture`, `sonarr_downloadclients_fixture`, `_mock_base_gets` helper)
    - tools/arrconf/arrconf/reconcilers/_shared.py (the new helper — Task 1's output is what these tests exercise)
    - tools/arrconf/arrconf/exceptions.py (ConfigError class to assert against)
    - tools/arrconf/arrconf/resources/sonarr/download_client.py (DownloadClient + FieldKV models for fixture construction)
  </read_first>
  <behavior>
    The test file is a NEW dedicated file (do not pollute the 47KB `test_reconcilers_sonarr.py`). It exercises `_resolve_qbit_credentials_from_env` directly via unit tests (no respx for tests 1-5 below — they're pure-Python helper tests; respx is only needed for the SC#3 idempotence test which exercises the full sonarr reconcile flow):

    - **test_yaml_empty_env_set_uses_env_values** (SC#2 case a):
      Build a DC with `fields=[FieldKV(name="host", value="x"), FieldKV(name="username", value=""), FieldKV(name="password", value="")]`. Monkeypatch `QBT_USER="qbituser"` + `QBT_PASS="qbitpass"`. Call helper. Assert returned DC's `fields[name=username].value == "qbituser"` and `fields[name=password].value == "qbitpass"`. Assert `host` field is unchanged (`value == "x"`). Assert input DC was not mutated.

    - **test_yaml_explicit_env_ignored** (SC#2 case b):
      Build a DC with `fields=[FieldKV(name="username", value="explicit-user"), FieldKV(name="password", value="explicit-pass")]`. Monkeypatch `QBT_USER="should-not-be-used"` + `QBT_PASS="should-not-be-used"`. Call helper. Assert returned DC's `fields[name=username].value == "explicit-user"` and `fields[name=password].value == "explicit-pass"`. Env is IGNORED.

    - **test_yaml_partial_username_explicit_password_empty** (SC#2 case c):
      Build a DC with `fields=[FieldKV(name="username", value="explicit-user"), FieldKV(name="password", value="")]`. Monkeypatch `QBT_PASS="from-env"`. (Leave `QBT_USER` unset or to any value — it should be ignored since YAML has explicit value.) Call helper. Assert `username == "explicit-user"` (YAML wins) and `password == "from-env"` (env injected).

    - **test_yaml_empty_env_unset_raises_config_error** (D-18-FAIL-FAST-01):
      Build a DC named "qBittorrent-tv" with `fields=[FieldKV(name="username", value=""), ...]`. Monkeypatch with `monkeypatch.delenv("QBT_USER", raising=False)` AND `monkeypatch.delenv("QBT_PASS", raising=False)`. Use `pytest.raises(ConfigError) as exc_info` and assert the message contains the substring `"download_client 'qBittorrent-tv'"` AND `"username is empty in YAML AND QBT_USER env is unset/empty"`.

    - **test_second_apply_zero_drift_on_download_clients_with_env_injected_creds** (SC#3 idempotence — respx-based):
      This is the "explicit respx test for the combo env-inject + 2nd-run idempotence" per D-18-IDEMPOTENCE-FREE. Use the same fixture pattern as `test_dump_apply_no_op` in `test_reconcilers_sonarr.py` (around line 79). Setup:
      1. Monkeypatch `QBT_USER="qbituser"` + `QBT_PASS="qbitpass"`.
      2. Mock GET `/downloadclient` to return a cluster-side DC whose `fields[]` has `username` and `password` with `privacy="password"` UI metadata + `value="********"` (Sonarr's mask) — this simulates an already-created DC.
      3. The desired DC (from `derived.download_clients`, fed by the generator) has `username: ""` + `password: ""` — Phase 18 helper will inject `"qbituser"` + `"qbitpass"`.
      4. Mock the rest of the base GETs via the existing `_mock_base_gets` helper (or inline if conftest doesn't expose it).
      5. Assert that the respx PUT route on `/downloadclient/{id}` is NOT called (the existing `merge_fields_for_put` at `differ.py:148` omits credential fields by privacy metadata so the post-injection desired body is byte-equivalent to current in the diff comparison → 0 plan_action).
      6. Use `respx_mock.put("/downloadclient/...").mock(return_value=httpx.Response(200, json={}))` then assert `put_route.called is False` and `put_route.call_count == 0`.

    Pytest discovers the file via `test_*.py` naming. Use `pytest.fixture` for the monkeypatch + fresh-env setup, follow existing import conventions (`import httpx; import pytest; import respx; from arrconf...`).
  </behavior>
  <action>
    Create `tools/arrconf/tests/test_qbit_credentials_env_fallback.py` with the 5 tests above. Conventions to honor:

    1. Module docstring:
       ```python
       """Tests for _resolve_qbit_credentials_from_env helper (Phase 18 — REQ-qbit-post-credentials).

       Covers:
       - SC#2 case (a): YAML empty + env set → env values injected.
       - SC#2 case (b): YAML explicit + env set → YAML wins, env ignored.
       - SC#2 case (c): YAML partial (username explicit + password empty) + QBT_PASS env set
         → username from YAML, password from env.
       - D-18-FAIL-FAST-01: YAML empty + env unset → ConfigError naming the DC entry.
       - SC#3 idempotence: 2nd arrconf apply with env-injected creds emits 0 plan_action
         on download_clients (acquired by construction via differ.merge_fields_for_put
         at differ.py:148 — this test is the dispositive proof).
       """
       ```

    2. Imports:
       ```python
       from __future__ import annotations

       import httpx
       import pytest
       import respx

       from arrconf.exceptions import ConfigError
       from arrconf.reconcilers._shared import _resolve_qbit_credentials_from_env
       from arrconf.resources.sonarr.download_client import DownloadClient, FieldKV
       ```

    3. Tests 1-4 (unit tests): use pytest `monkeypatch` fixture; build a `DownloadClient(name=..., protocol="torrent", implementation="QBittorrent", configContract="QBittorrentSettings", fields=[...])` per test. The tests run without respx — the helper is a pure transform, no HTTP.

    4. Test 5 (SC#3 idempotence): use the `@respx.mock` decorator pattern from `test_reconcilers_sonarr.py`. If `_mock_base_gets` is in conftest, use it; if it's a private function in `test_reconcilers_sonarr.py`, replicate its base GET setup inline. The key assertions:
       - `respx_mock.put(url__regex=r".*/downloadclient/\d+").mock(return_value=httpx.Response(200, json={}))` — capture as `put_route`
       - After the reconcile call, `assert put_route.call_count == 0`
       - This proves that `merge_fields_for_put` correctly omits the credential fields from the PUT body, so the differ sees no drift even when desired's username/password are env-injected values vs cluster's masked `"********"`.

    5. If the existing `_mock_base_gets` helper is in `test_reconcilers_sonarr.py` (not conftest), inline a minimal copy for test 5 — DO NOT import private symbols from another test file. Adequate scope: mock `/tag`, `/indexer`, `/rootfolder`, `/downloadclient`, `/notification`, `/remotepathmapping`, `/series` with the minimum JSON payloads to satisfy the reconciler. The downloadclient mock must include `fields` with `privacy="password"` metadata on the username + password entries so the differ knows to omit them.

    6. DO NOT modify any existing test file. DO NOT modify conftest.py to add shared fixtures. Keep this new file self-contained — the 5 tests will live or die together.
  </action>
  <verify>
    <automated>cd /data/projets/perso/arr-stack/tools/arrconf &amp;&amp; uv run pytest tests/test_qbit_credentials_env_fallback.py -v --no-cov</automated>
  </verify>
  <acceptance_criteria>
    - File `tools/arrconf/tests/test_qbit_credentials_env_fallback.py` exists
    - `grep -c "^def test_" tools/arrconf/tests/test_qbit_credentials_env_fallback.py` returns `5`
    - `grep -q "def test_yaml_empty_env_set_uses_env_values" tools/arrconf/tests/test_qbit_credentials_env_fallback.py` succeeds
    - `grep -q "def test_yaml_explicit_env_ignored" tools/arrconf/tests/test_qbit_credentials_env_fallback.py` succeeds
    - `grep -q "def test_yaml_partial_username_explicit_password_empty" tools/arrconf/tests/test_qbit_credentials_env_fallback.py` succeeds
    - `grep -q "def test_yaml_empty_env_unset_raises_config_error" tools/arrconf/tests/test_qbit_credentials_env_fallback.py` succeeds
    - `grep -q "def test_second_apply_zero_drift_on_download_clients_with_env_injected_creds" tools/arrconf/tests/test_qbit_credentials_env_fallback.py` succeeds
    - `grep -q "pytest.raises(ConfigError)" tools/arrconf/tests/test_qbit_credentials_env_fallback.py` succeeds
    - `grep -q "monkeypatch.setenv" tools/arrconf/tests/test_qbit_credentials_env_fallback.py` succeeds
    - `grep -q "monkeypatch.delenv" tools/arrconf/tests/test_qbit_credentials_env_fallback.py` succeeds
    - `cd tools/arrconf && uv run pytest tests/test_qbit_credentials_env_fallback.py -v --no-cov` exits 0 with 5 tests passed
    - `cd tools/arrconf && uv run ruff format --check tests/test_qbit_credentials_env_fallback.py` exits 0
    - `cd tools/arrconf && uv run ruff check tests/test_qbit_credentials_env_fallback.py` exits 0
    - `cd tools/arrconf && uv run mypy tests/test_qbit_credentials_env_fallback.py` exits 0
  </acceptance_criteria>
  <done>5 tests in `test_qbit_credentials_env_fallback.py` all pass green: 3 cover SC#2 (env-set, YAML-explicit, partial), 1 covers D-18-FAIL-FAST-01 ConfigError shape, 1 covers SC#3 idempotence via respx with cluster-masked credential fields. File passes triad cleanly.</done>
</task>

<task type="auto">
  <name>Task 4: Co-bump charts/arr-stack/values.yaml arrconf.image.tag 0.10.0 → 0.10.1</name>
  <files>charts/arr-stack/values.yaml</files>
  <read_first>
    - charts/arr-stack/values.yaml:440-460 (the arrconf.image block — read to see the exact 4-space-indent YAML structure and the Renovate annotation placement)
    - CLAUDE.md (sections "Release pin co-bump pattern" + the warning "Critique: ne jamais supprimer ni déplacer l'annotation `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` au-dessus de `repository:`")
  </read_first>
  <action>
    Edit `charts/arr-stack/values.yaml`. The change is one line, in the `arrconf.image` block (around line 451).

    Before (verbatim — 3 lines at 449-451):
    ```
            # renovate: image=ghcr.io/tom333/arr-stack-arrconf
            repository: ghcr.io/tom333/arr-stack-arrconf
            tag: "0.10.0"
    ```

    After (the only change is the tag value `0.10.0 → 0.10.1`):
    ```
            # renovate: image=ghcr.io/tom333/arr-stack-arrconf
            repository: ghcr.io/tom333/arr-stack-arrconf
            tag: "0.10.1"
    ```

    Constraints (D-18-CHART-BUMP-01 + CLAUDE.md "Release pin co-bump pattern"):
    1. Patch bump only (bugfix, not feature): `0.10.0 → 0.10.1`, NOT `0.10.0 → 0.11.0` or `0.10.0 → 1.0.0`.
    2. Preserve `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` annotation byte-for-byte, immediately above the `repository:` line (Renovate parser depends on this).
    3. Preserve YAML structure: same 12-space indent, same quoting style (`"0.10.1"` with double quotes — match the original).
    4. Do NOT modify any other `tag:` line in `values.yaml` (other apps: sonarr, radarr, prowlarr, qbittorrent, seerr, jellyfin, suggestarr, flaresolverr, cleanuparr — their tags are owned by Renovate, not by Phase 18).
    5. Do NOT modify `charts/arr-stack/Chart.yaml` (`version: 0.1.0` stays — auto-tag handles chart-side semver on push to main).

    This change MUST be in the same commit as the Python code changes (Tasks 1-3) per CLAUDE.md "Release pin co-bump pattern" — operator handles commit boundaries in the final commit step after all tasks pass.
  </action>
  <verify>
    <automated>cd /data/projets/perso/arr-stack &amp;&amp; grep -q 'tag: "0.10.1"' charts/arr-stack/values.yaml &amp;&amp; ! grep -q 'tag: "0.10.0"' charts/arr-stack/values.yaml &amp;&amp; grep -B 2 'tag: "0.10.1"' charts/arr-stack/values.yaml | grep -q "# renovate: image=ghcr.io/tom333/arr-stack-arrconf" &amp;&amp; helm dependency build charts/arr-stack/ &amp;&amp; helm lint charts/arr-stack/ -f examples/values-prod.yaml</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'tag: "0.10.1"' charts/arr-stack/values.yaml` returns exactly `1` (one occurrence — the arrconf bump)
    - `grep -c 'tag: "0.10.0"' charts/arr-stack/values.yaml` returns `0` (old value gone)
    - `grep -B 2 'tag: "0.10.1"' charts/arr-stack/values.yaml | grep -q "# renovate: image=ghcr.io/tom333/arr-stack-arrconf"` succeeds (annotation preserved 2 lines above the bumped tag — same as before)
    - `grep -A 1 "# renovate: image=ghcr.io/tom333/arr-stack-arrconf" charts/arr-stack/values.yaml | grep -q "repository: ghcr.io/tom333/arr-stack-arrconf"` succeeds (annotation still directly above repository line — Renovate parser invariant)
    - `git diff --stat charts/arr-stack/values.yaml` shows `1 insertion(+), 1 deletion(-)` (only the tag line changed; nothing else in values.yaml touched)
    - `cd /data/projets/perso/arr-stack && helm dependency build charts/arr-stack/ 2>&1 | tail -5 | grep -qE "(Saving|Deleting|outdated|up to date)"` indicates helm deps still resolvable (no chart schema breakage from this edit)
    - `cd /data/projets/perso/arr-stack && helm lint charts/arr-stack/ -f examples/values-prod.yaml 2>&1 | grep -q "0 chart(s) failed"` succeeds (chart still lint-clean after the bump)
  </acceptance_criteria>
  <done>`charts/arr-stack/values.yaml#arrconf.image.tag` reads `"0.10.1"` (was `"0.10.0"`), Renovate annotation preserved verbatim 2 lines above the bumped tag (directly above repository: line), no other tag in the file modified, `helm lint` still clean.</done>
</task>

<task type="auto">
  <name>Task 5: Run mandatory Triade Python gate from tools/arrconf/ (ruff format + ruff check + mypy + pytest with cov ≥ 70%)</name>
  <files>(no file modifications — gate-only task; if any check fails, fix the offending file and re-run)</files>
  <read_first>
    - CLAUDE.md (the "Triade Python (obligatoire avant tout commit Python)" section — exact commands to run, exact working directory)
    - tools/arrconf/pyproject.toml (verify the pytest config and coverage threshold)
  </read_first>
  <action>
    From `tools/arrconf/` working directory, run the full triad sequentially in one command chain — exact equivalent of what the CI `test` job runs in `.github/workflows/tests.yml`:

    ```bash
    cd /data/projets/perso/arr-stack/tools/arrconf && \
      uv run ruff format --check . && \
      uv run ruff check . && \
      uv run mypy . && \
      uv run pytest --cov-fail-under=70
    ```

    Steps and remediation:
    1. `uv run ruff format --check .` — if it fails, run `uv run ruff format .` (without `--check`) to apply formatting, then re-run the full chain.
    2. `uv run ruff check .` — if it fails, address each lint error individually (do NOT bulk-`--fix` blindly; the line `from arrconf.exceptions import ConfigError, ReconcileError` may need an `# noqa` if both aren't used yet — but both ARE used per Task 1 + Task 3).
    3. `uv run mypy .` — if it fails on the new helper, the most likely cause is the `Any` type from `_shared.py`'s existing patterns. The helper signature `(items: list[Any]) -> list[Any]` mirrors `_resolve_download_client_tag_labels` exactly, so mypy should accept it. If a new strict error appears, fix the offending line.
    4. `uv run pytest --cov-fail-under=70` — runs the FULL test suite (all 394+ existing tests PLUS the 5 new tests from Task 3). The 70% cov gate is the existing project floor; the new helper is small (~30 LOC) and fully covered by 5 tests, so cov should rise slightly, not fall.

    Stop on the first failure. Do not pass `--no-cov` or `-x` to the final pytest run — the full coverage gate is the CI's gate.
  </action>
  <verify>
    <automated>cd /data/projets/perso/arr-stack/tools/arrconf &amp;&amp; uv run ruff format --check . &amp;&amp; uv run ruff check . &amp;&amp; uv run mypy . &amp;&amp; uv run pytest --cov-fail-under=70</automated>
  </verify>
  <acceptance_criteria>
    - `cd tools/arrconf && uv run ruff format --check .` exits 0
    - `cd tools/arrconf && uv run ruff check .` exits 0
    - `cd tools/arrconf && uv run mypy .` exits 0 (or warns but exits 0; no error-level diagnostics)
    - `cd tools/arrconf && uv run pytest --cov-fail-under=70` exits 0
    - Total test count is `>=` 399 (previous baseline 394 tests in Phase 16 SC#3 + 5 new tests from Task 3)
    - Coverage report shows `tools/arrconf/arrconf/reconcilers/_shared.py` at `>=` its pre-Phase-18 line count (the helper's 30 new LOC are tested → no new uncovered lines)
    - No `FAILED` lines in pytest output
    - No `error:` lines in mypy output
  </acceptance_criteria>
  <done>All 4 triad commands exit 0 from `tools/arrconf/`. Test count is `>= 399`. Cov stays at or above 70%. This is the gate that proves the Python work is CI-ready before commit.</done>
</task>

<task type="auto">
  <name>Task 6: Write 18-HUMAN-UAT.md operator runbook covering SC#1-5</name>
  <files>.planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md</files>
  <read_first>
    - .planning/phases/18-qbit-post-credentials-fallback/18-CONTEXT.md (the "HUMAN-UAT Scenarios" section — 5 scenarios already drafted, just need to format them as a proper runbook)
    - .planning/phases/16-jellyfin-categories-as-libs/16-HUMAN-UAT.md (if it exists — use it as a structural template for the runbook format. If it doesn't exist, fall back to .planning/phases/11-operational-polish-bundle/ artifacts as a template)
    - CLAUDE.md (the "Workflow snapshot" section — Phase 18 UAT should NOT require new snapshots since it's a bugfix, just kubectl logs reading)
  </read_first>
  <action>
    Create `.planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md` with the 5 scenarios from CONTEXT.md, formatted as a runbook. Required structure:

    ```markdown
    # Phase 18 — qBit POST credentials fallback — HUMAN-UAT

    **Phase:** 18
    **Status:** Pending operator validation
    **Date:** 2026-05-24
    **Triggered after:** ArgoCD sync of the chart with arrconf image `:0.10.1` (post-merge of the Phase 18 PR)

    ## Pre-requisites

    - `arr-stack` PR for Phase 18 merged to main
    - `mathieudutour/github-tag-action` auto-tag CI ran on the merge commit and created `vX.Y.Z` (patch bump because `fix:` / `chore:` commits, or minor if `feat:` — operator inspects the GitHub Releases page)
    - `arrconf-image.yml` GHCR build ran and pushed `:0.10.1` (operator verifies via `https://github.com/users/tom333/packages/container/arr-stack-arrconf/versions`)
    - Renovate on `my-kluster` opened a PR bumping `targetRevision: vX.Y.Z` on `argocd/argocd-apps/arr-stack-app.yaml` (operator merges it)
    - ArgoCD sync completed (operator verifies `kubectl -n argocd get application arr-stack -o jsonpath='{.status.sync.status}'` returns `Synced`)

    ## Scenarios

    ### SC#1 (mandatory) — Generator preserves empty credential fields in arrconf.yml

    **Pre-condition:** Phase 18 chart deployed (no operator-side edit needed for this scenario).

    **Action:** None — just visual confirmation that the generator continues to emit `""` for username/password.

    **Verification:**
    ```bash
    kubectl -n selfhost exec deployment/arrconf-debug -- cat /app/config/arrconf.yml | grep -A 2 "username" | head -20
    ```
    (Or, if no arrconf-debug Deployment exists, read the ConfigMap directly:)
    ```bash
    kubectl -n selfhost get configmap arrconf-config -o jsonpath='{.data.arrconf\.yml}' | grep -A 2 "username" | head -20
    ```
    **Expected:** No explicit `username:` or `password:` values for qBit `download_clients` entries — the generator's `""` empty strings dominate (or the fields are entirely absent from the rendered fields[] list, depending on generator behavior).

    **Pass criterion:** No live credentials in the ConfigMap.

    ### SC#2 (mandatory) — ArgoCD-triggered CronJob does NOT raise ConfigError

    **Pre-condition:** SC#1 passed. arrconf-env SealedSecret has QBT_USER + QBT_PASS populated (Phase 5 baseline).

    **Action:** Wait for the next scheduled `arrconf` CronJob firing (or trigger it manually):
    ```bash
    kubectl -n selfhost create job --from=cronjob/arrconf arrconf-uat-sc2-$(date +%s)
    ```

    **Verification:**
    ```bash
    POD=$(kubectl -n selfhost get pods -l job-name=arrconf-uat-sc2-* -o jsonpath='{.items[0].metadata.name}' --sort-by='.metadata.creationTimestamp' | tail -1)
    kubectl -n selfhost logs $POD | grep -iE "(ConfigError|missing_env|exit code 2)"
    ```
    **Expected:** Empty output (no error lines).

    **Pass criterion:** The Job pod exits 0. Logs contain `apply_complete` events for sonarr + radarr.

    ### SC#3 (mandatory — dispositive) — Sonarr UI "Test" button on qBit DCs returns HTTP 200

    **Pre-condition:** SC#2 passed.

    **Action:** Open Sonarr UI at `https://sonarr.tgu.ovh/settings/downloadclients`. For each of the 3 qBit DCs visible (`qBittorrent-tv`, `qBittorrent-anime`, `qBittorrent-family`), click the "Test" button.

    **Verification:** Each "Test" button turns green with a ✓ checkmark. (HTTP 200 from qBittorrent to Sonarr's outbound auth probe.)

    **Pass criterion:** All 3 DCs test green. This is the dispositive proof that env-injection at POST time wrote real credentials into Sonarr's stored DC config, which Sonarr then uses to authenticate against qBittorrent.

    **Repeat for Radarr:** `https://radarr.tgu.ovh/settings/downloadclients` — same 3 buttons (categories may differ: `qBittorrent-movies`, `qBittorrent-anime`, `qBittorrent-family`).

    ### SC#4 (mandatory) — Second CronJob run emits 0 drift on download_clients (idempotence)

    **Pre-condition:** SC#3 passed.

    **Action:** Trigger a second manual run (or wait for the next scheduled CronJob firing):
    ```bash
    kubectl -n selfhost create job --from=cronjob/arrconf arrconf-uat-sc4-$(date +%s)
    ```

    **Verification:**
    ```bash
    POD=$(kubectl -n selfhost get pods -l job-name=arrconf-uat-sc4-* -o jsonpath='{.items[0].metadata.name}' --sort-by='.metadata.creationTimestamp' | tail -1)
    kubectl -n selfhost logs $POD | grep -E '"step":\s*"download_clients".*plan_action' | head -10
    ```
    **Expected:** Either no `plan_action` events on `download_clients` step, OR `actions=0` reported in the `apply_complete` event for sonarr + radarr (depending on the structlog event naming).

    **Pass criterion:** 0 add/update/delete actions on `download_clients` for both Sonarr and Radarr.

    ### SC#5 (optional follow-up) — Explicit YAML credentials override env

    **Pre-condition:** SC#1-4 passed. Operator wants to validate the explicit-YAML branch.

    **Action:** Edit `charts/arr-stack/files/arrconf.yml` to add `username` and `password` overrides on one qBit DC entry (e.g., add `fields: [{name: username, value: "explicit-user"}, {name: password, value: "explicit-pass"}]` to the relevant `download_clients[]` block in the `sonarr.main` or `radarr.main` section). Commit, PR, merge, sync.

    **Verification:**
    ```bash
    POD=$(kubectl -n selfhost get pods -l job-name=arrconf-* -o jsonpath='{.items[0].metadata.name}' --sort-by='.metadata.creationTimestamp' | tail -1)
    kubectl -n selfhost logs $POD | grep -E "update_field" | head -5
    ```
    **Expected:** A single `update_field` event on the affected DC name — Sonarr's `Test` button shows ✗ (because `explicit-pass` is wrong, but the field was POSTed verbatim per the helper's "YAML wins" branch). This is the proof that env is correctly ignored when YAML is explicit.

    **Pass criterion:** Explicit YAML values appear in the next reconcile cycle (revert this change after testing — restore generator-emitted empties for normal operation).

    ## Result tracking

    | Scenario | Status | Date | Notes |
    |----------|--------|------|-------|
    | SC#1 | ⏳ pending | — | — |
    | SC#2 | ⏳ pending | — | — |
    | SC#3 | ⏳ pending | — | — |
    | SC#4 | ⏳ pending | — | — |
    | SC#5 | ⏳ pending (optional) | — | — |

    ## Phase 18 close criteria

    Phase 18 closes when SC#1, SC#2, SC#3, SC#4 all pass. SC#5 is optional and non-blocking — it validates the "explicit YAML wins" branch which is already covered by `test_yaml_explicit_env_ignored` unit test.

    On close, update `.planning/STATE.md` and tick the Phase 18 checklist in `.planning/ROADMAP.md`.
    ```

    Tone: operator-runbook style (bash blocks, "Action / Expected / Pass criterion" structure per scenario). No emojis except the result table indicators. French/English bilingual is fine — match existing 16-HUMAN-UAT.md / 17-HUMAN-UAT.md if either exists.
  </action>
  <verify>
    <automated>test -f /data/projets/perso/arr-stack/.planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md &amp;&amp; [ "$(grep -c '^### SC#' /data/projets/perso/arr-stack/.planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md)" = "5" ] &amp;&amp; grep -q 'Pass criterion' /data/projets/perso/arr-stack/.planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md &amp;&amp; grep -q '0.10.1' /data/projets/perso/arr-stack/.planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md</automated>
  </verify>
  <acceptance_criteria>
    - File `.planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md` exists
    - `grep -c "^### SC#" .planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md` returns exactly `5` (one heading per scenario SC#1..SC#5)
    - `grep -q "Pass criterion" .planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md` succeeds (operator-decision lines present)
    - `grep -q "0.10.1" .planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md` succeeds (the runbook references the bumped image tag)
    - `grep -q "kubectl -n selfhost" .planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md` succeeds (real kubectl commands present, not pseudo-code)
    - `grep -q "ConfigError" .planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md` succeeds (SC#2 references the fail-fast signal to look for)
    - `grep -q "Test" .planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md` succeeds (SC#3 references the Sonarr "Test" button)
    - File length `>= 60` lines (substantial runbook, not a stub): `[ "$(wc -l < .planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md)" -ge 60 ]`
  </acceptance_criteria>
  <done>`18-HUMAN-UAT.md` exists with 5 scenarios (SC#1..SC#5), each with Pre-condition / Action / Verification / Pass criterion sections, real kubectl commands, references to the bumped image tag `0.10.1`, and a result-tracking table. The runbook is the dispositive artifact for SC#5 from the ROADMAP (and the source for Phase 18 close-out).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| env vars → reconciler process | `QBT_USER` / `QBT_PASS` enter the arrconf Python process via Kubernetes `envFrom: secretRef` (sealed-secret `arrconf-env`). Untrusted at first inspection but considered trusted once admitted (operator-controlled SealedSecret in repo). |
| reconciler → Sonarr/Radarr API | arrconf POSTs credentials in clear inside the cluster network (HTTP, no TLS between services). Trust boundary; mitigated by network-policy + ServiceAccount scoping in the cluster — out of scope for Phase 18. |
| arrconf code → ConfigError → operator logs | The error message includes the offending DC `name` (e.g. `qBittorrent-tv`) but NEVER includes the env var VALUE or the YAML field value. This is intentional — disclosure surface is the DC name only. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-18-01 | Information Disclosure | `ConfigError` message in stderr/structlog | mitigate | Message format from D-18-FAIL-FAST-01 (`f"download_client '{dc.name}': username is empty in YAML AND QBT_USER env is unset/empty"`) includes ONLY the DC `name` — no credential values. Task 1 acceptance criteria pin this exact string via grep; Task 3 test `test_yaml_empty_env_unset_raises_config_error` asserts the message substring without leaking values. |
| T-18-02 | Tampering | env var injection into POST body | mitigate | Helper reads `os.environ.get(...)` directly per-call (no module-level cache, no settings.py routing). pytest can monkeypatch.setenv to validate behavior; production K8s injection is via `envFrom: secretRef` — operator-controlled. |
| T-18-03 | Information Disclosure | structlog event emitted on env injection | accept | The current helper as specified does NOT emit a structlog event on env-substitution (no `log.info(...)` call). Adding one would risk logging the DC name routinely, which is already low-risk but unnecessary noise. Operator UAT (SC#3 Sonarr "Test" button green) is the observability signal. If a future debug need arises, add a non-default-DEBUG event. |
| T-18-04 | Repudiation | git commit hides chart-pin co-bump | mitigate | CLAUDE.md "Release pin co-bump pattern" mandates same-commit Python + values.yaml bump. Task 4 acceptance criteria pin the exact value (`tag: "0.10.1"`); the GitOps trail (commit hash → auto-tag → GHCR build → Renovate PR on my-kluster) is the audit chain. |
| T-18-05 | Denial of Service | malformed env (only QBT_USER set, QBT_PASS unset) causes mid-reconcile crash | accept | This is exactly the D-18-FAIL-FAST-01 contract — fail-fast `ConfigError` with `Exit(code=2)` is the desired behavior (anti-D-02.2-AUTH-REGRESSION). The CronJob's retry semantics (backoffLimit) handle transient outages; the operator notices via missing CI green or missing `apply_complete` event. |
| T-18-06 | Elevation of Privilege | helper accidentally injects env into a non-qBit DC (e.g., a Transmission DC) | mitigate | Helper's field-walk only substitutes when `f.name in {"username", "password"}` AND `f.value` is empty. Non-qBit DCs (Transmission, NZBGet) ALSO have `username`/`password` fields by Sonarr API design. **Risk:** if the operator adds a Transmission DC, the helper would inject QBT_USER into its username field. **Disposition:** Accept as scope-aligned bug — Categories generator only produces qBit DCs today; if operator adds a Transmission DC manually in arrconf.yml, they will set explicit creds (or get a clear `ConfigError` naming the DC). Mitigation deferred to v0.6.x if SC arises. Documented here for traceability. |
</threat_model>

<verification>
## Phase-level checks (run after all 6 tasks complete)

1. **Source audit:** every Success Criterion has a covering task:
   - SC#1 (env injection + fail-fast) → Task 1 (helper) + Task 2 (wiring)
   - SC#2 (3 respx cases) → Task 3 (5 tests, of which 3 are SC#2 cases)
   - SC#3 (idempotence) → Task 3 (test_second_apply_zero_drift_on_download_clients_with_env_injected_creds) + reliance on existing `merge_fields_for_put` at `differ.py:148`
   - SC#4 (chart-pin co-bump) → Task 4 (values.yaml bump)
   - SC#5 (operator UAT) → Task 6 (18-HUMAN-UAT.md)
   - Triad gate (CLAUDE.md mandatory) → Task 5

2. **Source consistency (CONTEXT.md):**
   - D-18-INJECT-LOC-01 (helper in `_shared.py`) → Task 1
   - D-18-FAIL-FAST-01 (ConfigError exact message) → Task 1 + Task 3 test 4
   - D-18-SCOPE-01 (Sonarr AND Radarr) → Task 2 (both files)
   - D-18-IDEMPOTENCE-FREE (no new idempotence code) → Task 3 test 5 (asserts existing `merge_fields_for_put` does the job)
   - D-18-CHART-BUMP-01 (patch bump, annotation preserved) → Task 4

3. **Scope discipline (locked boundaries from CONTEXT.md):**
   - `grep -c "_resolve_qbit_credentials_from_env" tools/arrconf/arrconf/generators/categories.py` returns 0
   - `grep -c "_resolve_qbit_credentials_from_env" tools/arrconf/arrconf/differ.py` returns 0
   - `grep -c "_resolve_qbit_credentials_from_env" tools/arrconf/arrconf/__main__.py` returns 0
   - `git diff --stat charts/arr-stack/files/arrconf.yml` returns empty (file untouched)
   - `git diff --stat .github/workflows/` returns empty (no CI changes)

4. **End-to-end triad (re-run after final touches):**
   - `cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy . && uv run pytest --cov-fail-under=70` exits 0
   - `helm dependency build charts/arr-stack/ && helm lint charts/arr-stack/ -f examples/values-prod.yaml` exits 0
</verification>

<success_criteria>
- All 6 tasks complete with their `<acceptance_criteria>` met.
- `tools/arrconf/arrconf/reconcilers/_shared.py` has the new `_resolve_qbit_credentials_from_env` helper, mirroring `_resolve_download_client_tag_labels` shape, raising `ConfigError` per D-18-FAIL-FAST-01.
- Both `sonarr.py` and `radarr.py` invoke the helper exactly once each, in the download_clients step, between label resolution and managed-tag stamping.
- `tests/test_qbit_credentials_env_fallback.py` exists with 5 passing tests covering SC#2 (3 cases) + D-18-FAIL-FAST-01 ConfigError + SC#3 idempotence.
- `charts/arr-stack/values.yaml#arrconf.image.tag` is `"0.10.1"` (was `"0.10.0"`), Renovate annotation preserved verbatim, `helm lint` clean.
- Triade Python green from `tools/arrconf/`: `ruff format --check .`, `ruff check .`, `mypy .`, `pytest --cov-fail-under=70` all exit 0.
- `.planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md` exists with 5 operator scenarios.
- Scope boundaries verified: no changes to `generators/categories.py`, `differ.py`, `__main__.py`, `arrconf.yml`, or `.github/workflows/*.yml`.
- This plan's REQ-qbit-post-credentials is fully covered; ROADMAP Phase 18 checklist can be ticked once operator UAT (SC#1-5) signs off.
</success_criteria>

<output>
After completion, create `.planning/phases/18-qbit-post-credentials-fallback/18-A-SUMMARY.md` describing:
- Helper added (file + signature + lines)
- Call sites wired (sonarr.py + radarr.py, line numbers)
- Tests added (5 tests, file path)
- Chart-pin bump applied (0.10.0 → 0.10.1)
- Triad result (test count, coverage %, mypy/ruff status)
- HUMAN-UAT runbook path
- Operator next steps (push main → wait for auto-tag → wait for GHCR build → merge Renovate PR on my-kluster → ArgoCD sync → run UAT scenarios SC#1-5)
</output>
