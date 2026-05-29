"""Configarr-shape structured diff (D-05 / D-06 / SC#4).

Produces a structured diff suitable for the frontend to render changes to
configarr.yml. Groups changes per-quality-profile and per-custom-format
(configarr's semantic units), NOT by arrconf's ``categories`` + ``APP_SECTIONS``.

D-05 boundary: this module does NOT import ``arrconf_ui.diff`` — that module
is hard-coded to arrconf's shape (categories + sonarr/radarr/prowlarr/...).

SC#4 / D-06: the diff MUST operate on tag-literal data (output of
``_tagged_to_literal``). The ``before`` snapshot is obtained via
``_tagged_to_literal(read_yaml(...))``. The ``after`` payload is already
tag-literal strings from the API caller. This module NEVER resolves env vars,
NEVER calls os.environ / getenv, and NEVER routes data through ``model_dump``
(which would strip ``!env``/``!secret`` tags from api_key fields).

Return shape for ``configarr_diff``::

    {
      "top_level": {"changed_fields": ["trashGuideUrl", ...]},
      "customFormatDefinitions": {
          "<trash_id_or_name>": {"changed_fields": [...]}
      },
      "sonarr.main": {
          "changed_fields": [...],         # direct per-instance scalar fields
          "quality_profiles": {
              "<profile_name>": {"changed_fields": [...]},
              ...
          },
          "custom_formats": {
              "<trash_id>": {"changed_fields": [...]},
              ...
          },
      },
      "radarr.main": { ... },
      ...
    }

Sections with zero changes are STILL present (empty arrays/dicts) — the
frontend hides them. Keep the shape predictable.
"""

from __future__ import annotations

from typing import Any

# Top-level configarr scalar keys (compared as flat changed_fields)
_TOP_LEVEL_SCALAR_KEYS = ("trashGuideUrl", "recyclarrConfigUrl")

# Per-arr-instance sections within configarr (sonarr / radarr)
_ARR_SECTIONS = ("sonarr", "radarr")


# ---------------------------------------------------------------------------
# Helpers (adapted from arrconf_ui/diff.py — NOT imported; D-05 boundary)
# ---------------------------------------------------------------------------


def _list_to_index(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    """Index a list of dicts by a stable key (e.g., quality_profile.name)."""
    return {item[key]: item for item in items if key in item}


def _flatten_paths(prefix: str, value: Any) -> dict[str, Any]:
    """Walk a nested dict/list and return a flat {dotted.path: leaf_value} map."""
    out: dict[str, Any] = {}
    if isinstance(value, dict):
        for k, v in value.items():
            out.update(_flatten_paths(f"{prefix}.{k}" if prefix else k, v))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            out.update(_flatten_paths(f"{prefix}[{i}]", v))
    else:
        out[prefix] = value
    return out


def _changed_field_paths(before: Any, after: Any, prefix: str = "") -> list[str]:
    """Return sorted dotted-path list of leaves whose value differs between before and after."""
    before_flat = _flatten_paths(prefix, before)
    after_flat = _flatten_paths(prefix, after)
    paths: list[str] = []
    for key in sorted(set(before_flat) | set(after_flat)):
        if before_flat.get(key) != after_flat.get(key):
            paths.append(key)
    return paths


def _diff_list_by_key(
    before_list: list[dict[str, Any]],
    after_list: list[dict[str, Any]],
    key: str,
) -> dict[str, dict[str, Any]]:
    """Diff two lists matched by ``key``.

    Returns a dict ``{item_id: {"changed_fields": [...]}}`` for every item
    in either list. Items absent from one side are treated as empty dicts
    (all fields changed vs. nothing). Unchanged items get ``changed_fields: []``.
    """
    before_idx = _list_to_index(before_list, key)
    after_idx = _list_to_index(after_list, key)
    all_keys = sorted(set(before_idx) | set(after_idx))
    result: dict[str, dict[str, Any]] = {}
    for k in all_keys:
        changed = _changed_field_paths(before_idx.get(k, {}), after_idx.get(k, {}))
        result[k] = {"changed_fields": changed}
    return result


def _cf_stable_key(entry: dict[str, Any], idx: int) -> str:
    """Derive a stable key for a custom_formats[] entry.

    Priority: first element of ``trash_ids`` > ``trash_id`` > ``name`` > ``"[{idx}]"``.
    configarr per-instance custom_formats entries use ``trash_ids: list[str]``;
    customFormatDefinitions entries use ``trash_id: str``.
    """
    trash_ids = entry.get("trash_ids")
    if trash_ids and isinstance(trash_ids, list) and trash_ids:
        return str(trash_ids[0])
    if "trash_id" in entry:
        return str(entry["trash_id"])
    if "name" in entry:
        return str(entry["name"])
    return f"[{idx}]"


def _diff_cf_list(
    before_list: list[dict[str, Any]],
    after_list: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Diff two custom_formats[] lists using a derived stable key.

    Returns ``{key: {"changed_fields": [...]}}`` for every entry in either list.
    """
    before_idx = {_cf_stable_key(item, i): item for i, item in enumerate(before_list)}
    after_idx = {_cf_stable_key(item, i): item for i, item in enumerate(after_list)}
    all_keys = sorted(set(before_idx) | set(after_idx))
    result: dict[str, dict[str, Any]] = {}
    for k in all_keys:
        changed = _changed_field_paths(before_idx.get(k, {}), after_idx.get(k, {}))
        result[k] = {"changed_fields": changed}
    return result


def _diff_instance(
    before_inst: dict[str, Any],
    after_inst: dict[str, Any],
) -> dict[str, Any]:
    """Compute a semantic diff for one arr-instance (e.g. sonarr.main).

    Groups changes into:
    - ``changed_fields``: scalar/structural fields that differ (excluding
      quality_profiles and custom_formats, which get their own sections)
    - ``quality_profiles``: per-profile diff indexed by ``name``
    - ``custom_formats``: per-custom-format diff indexed by ``trash_id``
      (falling back to index position string if trash_id absent)
    """
    result: dict[str, Any] = {}

    # Scalar fields — compare everything except the list sections
    skip_keys = {"quality_profiles", "custom_formats"}
    before_scalar = {k: v for k, v in before_inst.items() if k not in skip_keys}
    after_scalar = {k: v for k, v in after_inst.items() if k not in skip_keys}
    result["changed_fields"] = _changed_field_paths(before_scalar, after_scalar)

    # quality_profiles — indexed by name
    before_qp = before_inst.get("quality_profiles") or []
    after_qp = after_inst.get("quality_profiles") or []
    result["quality_profiles"] = _diff_list_by_key(before_qp, after_qp, key="name")

    # custom_formats — these entries have trash_ids (list) + assign_scores_to;
    # build a stable key from the first trash_id or index position
    before_cf = before_inst.get("custom_formats") or []
    after_cf = after_inst.get("custom_formats") or []
    result["custom_formats"] = _diff_cf_list(before_cf, after_cf)

    return result


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def configarr_diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Compute semantic diff between two configarr.yml dicts.

    Both inputs MUST be the output of ``_tagged_to_literal(read_yaml(...))``
    or equivalent (plain dicts with ``!env``/``!secret`` tags already
    reconstructed as literal strings). Never pass ``model_dump()`` output —
    that would silently drop the tag from ``api_key`` fields (D-06 / SC#4).

    Returns a nested dict (see module docstring for full shape). Sections with
    no changes are still present with empty lists/dicts — callers should use
    ``has_changes()`` to check for any meaningful delta.
    """
    out: dict[str, Any] = {}

    # Top-level scalar keys (trashGuideUrl, recyclarrConfigUrl)
    before_top = {k: before.get(k) for k in _TOP_LEVEL_SCALAR_KEYS}
    after_top = {k: after.get(k) for k in _TOP_LEVEL_SCALAR_KEYS}
    out["top_level"] = {"changed_fields": _changed_field_paths(before_top, after_top)}

    # customFormatDefinitions — indexed by trash_id
    before_cfd = before.get("customFormatDefinitions") or []
    after_cfd = after.get("customFormatDefinitions") or []
    out["customFormatDefinitions"] = _diff_list_by_key(before_cfd, after_cfd, key="trash_id")

    # Per-arr sections (sonarr / radarr) — each section is a dict of instances
    for section in _ARR_SECTIONS:
        before_sec = before.get(section) or {}
        after_sec = after.get(section) or {}
        all_instances = sorted(set(before_sec) | set(after_sec))
        for instance in all_instances:
            label = f"{section}.{instance}"
            out[label] = _diff_instance(
                before_sec.get(instance) or {},
                after_sec.get(instance) or {},
            )

    return out


def has_changes(diff: dict[str, Any]) -> bool:
    """Return True if the diff contains any non-empty change set.

    Checks:
    - ``top_level.changed_fields`` non-empty
    - any ``customFormatDefinitions`` item has non-empty ``changed_fields``
    - any ``sonarr.*`` / ``radarr.*`` instance has non-empty ``changed_fields``,
      ``quality_profiles.<name>.changed_fields``, or
      ``custom_formats.<name>.changed_fields``
    """
    # top_level scalar changes
    top = diff.get("top_level", {})
    if top.get("changed_fields"):
        return True

    # customFormatDefinitions
    for _item_id, item_diff in diff.get("customFormatDefinitions", {}).items():
        if isinstance(item_diff, dict) and item_diff.get("changed_fields"):
            return True

    # per-instance sections
    for key, value in diff.items():
        if key in ("top_level", "customFormatDefinitions"):
            continue
        if not isinstance(value, dict):
            continue
        # direct changed_fields on the instance
        if value.get("changed_fields"):
            return True
        # quality_profiles sub-section
        for _profile, pdiff in value.get("quality_profiles", {}).items():
            if isinstance(pdiff, dict) and pdiff.get("changed_fields"):
                return True
        # custom_formats sub-section
        for _cf, cfdiff in value.get("custom_formats", {}).items():
            if isinstance(cfdiff, dict) and cfdiff.get("changed_fields"):
                return True

    return False
