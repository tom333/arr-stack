"""Generic diff/reconcile engine.

Implements the 6-case classifier (ADD / UPDATE / DELETE / NO_OP / PRUNE_SKIP /
PRUNE_PROTECTED) per D-04 / D-11 / D-20. Idempotence golden rule: identical
input → identical plan → all NO_OP. Prune is opt-in (REQ-prune-opt-in) AND
gated by the ``arrconf-managed`` tag at delete time (REQ-managed-tag, T-01-04).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

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


def diff_models(a: BaseModel, b: BaseModel) -> list[str]:
    """Return sorted field names that differ (excluding D-21 read-only fields)."""
    a_dump = a.model_dump(exclude_none=True, exclude=_READ_ONLY_FIELDS)
    b_dump = b.model_dump(exclude_none=True, exclude=_READ_ONLY_FIELDS)
    return sorted({k for k in (set(a_dump) | set(b_dump)) if a_dump.get(k) != b_dump.get(k)})


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
