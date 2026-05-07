"""Generic diff/reconcile engine. Skeleton — full impl in Wave 2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel


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
    """Return field names that differ (excluding read-only fields per D-21).

    W2 fills body.
    """
    raise NotImplementedError("Wave 2 — Pattern 4 differ algorithm")


def reconcile[T: BaseModel](
    current: list[T],
    desired: list[T],
    *,
    match_key: str = "name",
    prune: bool = False,
    managed_tag_id: int | None = None,
) -> list[PlannedAction[T]]:
    """Run the generic reconcile algorithm.

    W2 fills body per D-04 / D-11 / D-20.
    """
    raise NotImplementedError("Wave 2 — Pattern 4 differ algorithm")
