"""Generic diff/reconcile engine.

Implements the 6-case classifier (ADD / UPDATE / DELETE / NO_OP / PRUNE_SKIP /
PRUNE_PROTECTED) per D-04 / D-11 / D-20. Idempotence golden rule: identical
input → identical plan → all NO_OP. Prune is opt-in (REQ-prune-opt-in) AND
gated by the ``arrconf-managed`` tag at delete time (REQ-managed-tag, T-01-04).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel

log = structlog.get_logger()

_READ_ONLY_FIELDS: set[str] = {
    "id",
    "implementationName",
    "infoLink",
    "message",
    "presets",
}

# D-36: Sonarr's privacy stand-in for password / apiKey / userName fields. Mirrored
# in dump.py as the same constant. The dump emitter drops these entries so they never
# reach committed YAML; this constant is kept here so that ``diff_models`` (and the
# round-trip contract) can normalize cluster state in the same way before comparing.
_REDACTED_VALUE = "***REDACTED***"


class Action(Enum):
    """Reconciliation outcomes (D-04 / D-09 / D-11)."""

    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"
    NO_OP = "no-op"
    PRUNE_SKIP = "prune-skip"
    PRUNE_PROTECTED = "prune-protected"


@dataclass
class PlannedAction[T: BaseModel]:
    """A single planned reconciliation step."""

    action: Action
    name: str
    current: T | None
    desired: T | None
    diff_fields: list[str]


def _strip_redacted_fields(dump: dict[str, Any]) -> dict[str, Any]:
    """Drop fields[] entries whose value is REDACTED — mirror of dump.py filter (D-36).

    Applied symmetrically on both sides of ``diff_models`` so the round-trip property
    (D-31/D-35/D-36) holds: dump emits without REDACTED, reload→reconcile compares
    cluster (post-strip) against desired (already post-strip from dump) → NO_OP.
    """
    if "fields" not in dump:
        return dump
    dump = dict(dump)
    dump["fields"] = [f for f in dump["fields"] if f.get("value") != _REDACTED_VALUE]
    return dump


def diff_models(a: BaseModel, b: BaseModel) -> list[str]:
    """Return sorted field names that differ (excluding D-21 read-only fields).

    Both sides are normalized via ``_strip_redacted_fields`` (D-36) so cluster's
    REDACTED ``fields[]`` entries — which the dump emitter omits — do not flag a
    spurious UPDATE on round-trip.
    """
    a_dump = _strip_redacted_fields(a.model_dump(exclude_none=True, exclude=_READ_ONLY_FIELDS))
    b_dump = _strip_redacted_fields(b.model_dump(exclude_none=True, exclude=_READ_ONLY_FIELDS))
    return sorted({k for k in (set(a_dump) | set(b_dump)) if a_dump.get(k) != b_dump.get(k)})


def merge_fields_for_put[T: BaseModel](current: T, desired: T) -> dict[str, Any]:
    """Merge cluster's stored field values into desired body for PUT (D-31/D-32/D-33).

    For each entry in ``desired.fields[]`` (matched by ``name``), if the YAML value is
    ``''`` or ``None``, take the corresponding cluster value. Otherwise keep desired's
    value. The rule is purely value-based (D-32): field NAMES are NOT consulted — there
    is no name-based allowlist of which fields qualify for the empty-preserve rule.

    ``tags`` is intentionally NOT merged (T-02.1-06): desired's tags list legitimately
    overrides cluster's because the reconciler appends ``managed_tag_id`` (D-02).

    Generic over ``T: BaseModel`` so Phase 3 Radarr/Prowlarr reconcilers can reuse it
    unchanged (D-33). Returns a dict ready for ``client.put(path, id=..., json=body)``;
    read-only fields (D-21) are excluded from the body, so callers must re-inject ``id``.

    v0.1.5 / D-02.2-AUTH-REGRESSION (ADR-8.1 refinement): if the cluster-side
    field metadata indicates a credential field (``privacy == "password"`` or
    ``"userName"``), the entry is OMITTED from the merged body entirely instead
    of being substituted with cluster's stored value. Sonarr's GET serializes
    credential fields with the API mask ``"********"``; substituting that mask
    into the PUT body (which v0.1.4's ``?forceSave=true`` then accepts verbatim)
    would overwrite the real stored credential with the literal mask token —
    the regression that triggered Plan 02.2 v0.1.5 hotfix. Sonarr preserves
    stored values when fields are absent, so omission is safer than passthrough.
    Emits ``merge_field_omitted_credential`` for cluster audit trails.

    Ordering invariant (T-02.2-08-02): the omit-credential branch MUST execute
    BEFORE the empty-value preserve-cluster branch in the per-field loop. The
    BEHAVIORAL test test_merge_fields_omits_privacy_password_when_value_is_in_tree_redacted_mask
    exercises a non-empty cluster value (``"***REDACTED***"``) that would
    otherwise hit the substitute branch first if the ordering broke.
    """
    cur_dump = current.model_dump(exclude_none=True)
    des_dump = desired.model_dump(exclude_none=True, exclude=_READ_ONLY_FIELDS)
    cur_by_name = {f["name"]: f for f in cur_dump.get("fields", [])}
    # v0.1.5 / D-02.2-AUTH-REGRESSION: build a parallel privacy lookup directly from
    # the pydantic model instances. ``FieldKV.privacy`` is declared with ``exclude=True``
    # (it is UI metadata not meant to round-trip into PUT bodies), so it does NOT appear
    # in ``cur_dump`` — but it IS stored on the model and is the load-bearing signal for
    # the omit-by-metadata strategy below. Reading it from ``current.fields`` keeps the
    # fix minimal-surface and avoids changing the FieldKV exclude policy.
    cur_privacy_by_name: dict[str, str | None] = {
        f.name: f.privacy for f in getattr(current, "fields", [])
    }
    merged_fields: list[dict[str, Any]] = []
    for des_f in des_dump.get("fields", []):
        cur_f = cur_by_name.get(des_f["name"])
        cur_privacy = cur_privacy_by_name.get(des_f["name"])
        # v0.1.5 / D-02.2-AUTH-REGRESSION: omit credential fields entirely (Option A).
        # Sonarr preserves stored values when a field is absent from the PUT body —
        # safer than substituting the API mask "********" via the merge_field_preserved
        # branch below. Audit event payload is metadata-only ({name, privacy}); the
        # field VALUE is never logged (T-02.2-08-01).
        if cur_privacy in ("password", "userName"):
            log.info(
                "merge_field_omitted_credential",
                name=des_f["name"],
                privacy=cur_privacy,
            )
            continue
        v = des_f.get("value")
        if v == "" or v is None:
            if cur_f is not None and cur_f.get("value") not in ("", None):
                merged = dict(des_f)
                merged["value"] = cur_f["value"]
                log.info("merge_field_preserved", name=des_f["name"])
                merged_fields.append(merged)
                continue
        merged_fields.append(des_f)
    des_dump["fields"] = merged_fields
    return des_dump


def reconcile[T: BaseModel](
    current: list[T],
    desired: list[T],
    *,
    match_key: str = "name",
    prune: bool = False,
    managed_tag_id: int | None = None,
) -> list[PlannedAction[T]]:
    """Run the generic reconcile algorithm.

    1. Match items by ``match_key`` (default ``"name"``, D-20).
    2. Classify ADD / UPDATE / NO_OP for desired items.
    3. For unmatched current items:
       - prune=False → PRUNE_SKIP (warn) — REQ-prune-opt-in / D-04
       - prune=True + managed_tag_id missing OR not in cur.tags → PRUNE_PROTECTED — D-02 / T-01-04
       - prune=True + managed_tag_id in cur.tags → DELETE
    """
    by_name_current: dict[str, T] = {getattr(c, match_key): c for c in current}
    by_name_desired: dict[str, T] = {getattr(d, match_key): d for d in desired}
    plan: list[PlannedAction[T]] = []

    for name, des in by_name_desired.items():
        cur = by_name_current.get(name)
        if cur is None:
            plan.append(PlannedAction(Action.ADD, name, None, des, []))
            log.info("plan_action", action="add", name=name)
        else:
            diffs = diff_models(cur, des)
            if diffs:
                plan.append(PlannedAction(Action.UPDATE, name, cur, des, diffs))
                log.info("plan_action", action="update", name=name, diff_fields=diffs)
            else:
                plan.append(PlannedAction(Action.NO_OP, name, cur, des, []))

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

    return plan
