"""Semantic diff comparator for arrconf.yml (D-07).

Produces a structured object suitable for the frontend to render as
"3 categories added, 2 modified, 1 removed" + per-section changed-field
lists. NOT a unified-diff text dump.

Comparison rules:
- top-level `categories` list: matched by `name` (stable identifier per
  MediaCategory.name docstring "Kebab-case slug. Stable match key.").
- per-app dicts (sonarr/radarr/...): matched by instance key (`main`).
  For each instance, recursively compare fields; flag any path whose
  value differs.
- Returns a dict shape:
    {
      "categories": {"added": [name, ...], "modified": [name, ...], "removed": [name, ...]},
      "sonarr.main": {"changed_fields": ["dotted.path", ...]},
      ...
    }
  Sections with zero changes are STILL present (empty arrays) — the
  frontend hides them. Keep the shape predictable.
"""

from __future__ import annotations

from typing import Any

# Top-level keys whose contents we compare per-section.
APP_SECTIONS = ("sonarr", "radarr", "prowlarr", "qbittorrent", "seerr", "jellyfin")


def _list_to_index(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    """Index a list of dicts by a stable key (e.g., category.name)."""
    return {item[key]: item for item in items if key in item}


def _flatten_paths(prefix: str, value: Any) -> dict[str, Any]:
    """Walk a nested dict/list and return a flat {dotted.path: leaf_value}."""
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
    """Return dotted-path list of leaves whose value differs."""
    before_flat = _flatten_paths(prefix, before)
    after_flat = _flatten_paths(prefix, after)
    paths: list[str] = []
    for key in sorted(set(before_flat) | set(after_flat)):
        if before_flat.get(key) != after_flat.get(key):
            paths.append(key)
    return paths


def diff_configs(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Compute semantic diff between two RootConfig JSON dicts.

    Both inputs are the output of `RootConfig.model_dump(mode='json')` or
    equivalent (plain dicts; no pydantic objects).

    Returns a dict per D-07 (see module docstring for shape).
    """
    out: dict[str, Any] = {}

    # categories list (matched by name)
    cat_before = _list_to_index(before.get("categories", []) or [], key="name")
    cat_after = _list_to_index(after.get("categories", []) or [], key="name")
    added_names = sorted(set(cat_after) - set(cat_before))
    removed_names = sorted(set(cat_before) - set(cat_after))
    modified_names = sorted(
        name for name in set(cat_before) & set(cat_after) if cat_before[name] != cat_after[name]
    )
    out["categories"] = {
        "added": added_names,
        "modified": modified_names,
        "removed": removed_names,
    }

    # per-app sections (sonarr/radarr/...): one entry per instance key
    for section in APP_SECTIONS:
        b_section = before.get(section, {}) or {}
        a_section = after.get(section, {}) or {}
        all_instances = sorted(set(b_section) | set(a_section))
        for instance in all_instances:
            label = f"{section}.{instance}"
            changed = _changed_field_paths(
                b_section.get(instance, {}),
                a_section.get(instance, {}),
                prefix=label,
            )
            out[label] = {"changed_fields": changed}

    return out


def has_changes(diff: dict[str, Any]) -> bool:
    """Return True if the diff contains any non-empty change set."""
    cats = diff.get("categories", {})
    if cats.get("added") or cats.get("modified") or cats.get("removed"):
        return True
    for k, v in diff.items():
        if k == "categories":
            continue
        if isinstance(v, dict) and v.get("changed_fields"):
            return True
    return False
