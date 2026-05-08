"""Unit tests for arrconf.differ.reconcile() — covers all 6 Action cases + read-only diff."""

from __future__ import annotations

from typing import Any

from arrconf.differ import Action, diff_models, merge_fields_for_put, reconcile
from arrconf.resources.sonarr.download_client import DownloadClient


def _dc(name: str, **kwargs: Any) -> DownloadClient:
    defaults: dict[str, Any] = {
        "protocol": "torrent",
        "implementation": "QBittorrent",
        "configContract": "QBittorrentSettings",
    }
    defaults.update(kwargs)
    return DownloadClient(name=name, **defaults)


def test_add() -> None:
    plan = reconcile(current=[], desired=[_dc("qbit")])
    assert [p.action for p in plan] == [Action.ADD]


def test_no_op() -> None:
    a, b = _dc("qbit", priority=1), _dc("qbit", priority=1)
    plan = reconcile(current=[a], desired=[b])
    assert plan[0].action == Action.NO_OP
    assert plan[0].diff_fields == []


def test_update() -> None:
    plan = reconcile(
        current=[_dc("qbit", priority=1)],
        desired=[_dc("qbit", priority=5)],
    )
    assert plan[0].action == Action.UPDATE
    assert "priority" in plan[0].diff_fields


def test_prune_skip_when_prune_false() -> None:
    plan = reconcile(current=[_dc("orphan")], desired=[], prune=False)
    assert plan[0].action == Action.PRUNE_SKIP


def test_prune_protected_when_no_managed_tag() -> None:
    cur = _dc("orphan", tags=[5])
    plan = reconcile(current=[cur], desired=[], prune=True, managed_tag_id=99)
    assert plan[0].action == Action.PRUNE_PROTECTED


def test_prune_executed_when_tag_present() -> None:
    cur = _dc("orphan", tags=[99])
    plan = reconcile(current=[cur], desired=[], prune=True, managed_tag_id=99)
    assert plan[0].action == Action.DELETE


def test_diff_models_excludes_readonly() -> None:
    a = _dc("qbit", priority=1)
    b = _dc("qbit", priority=1)
    b.id = 42  # read-only field — must be excluded from diff (D-21)
    assert diff_models(a, b) == []


def test_diff_models_detects_field_change() -> None:
    a = _dc("qbit", priority=1)
    b = _dc("qbit", priority=5)
    assert diff_models(a, b) == ["priority"]


def test_no_managed_tag_id_treats_as_protected() -> None:
    """If managed_tag_id is None, prune=True must STILL not delete (T-01-04 defensive default)."""
    cur = _dc("orphan", tags=[42])
    plan = reconcile(current=[cur], desired=[], prune=True, managed_tag_id=None)
    assert plan[0].action == Action.PRUNE_PROTECTED


# --- merge_fields_for_put tests (D-31 / D-32 / D-33 / D-35) ---------------------------------


def test_merge_preserves_cluster_value_when_yaml_empty() -> None:
    """D-31: cluster has REDACTED password, YAML has '' — PUT body must carry REDACTED."""
    cur = _dc("qbit", fields=[{"name": "password", "value": "***REDACTED***"}])
    des = _dc("qbit", fields=[{"name": "password", "value": ""}])
    merged = merge_fields_for_put(cur, des)
    by_name = {f["name"]: f["value"] for f in merged["fields"]}
    assert by_name == {"password": "***REDACTED***"}


def test_merge_uses_yaml_value_when_non_empty() -> None:
    """D-31: non-empty YAML value wins over cluster value (apply path is authoritative)."""
    cur = _dc("qbit", fields=[{"name": "host", "value": "old.local"}])
    des = _dc("qbit", fields=[{"name": "host", "value": "new.local"}])
    merged = merge_fields_for_put(cur, des)
    by_name = {f["name"]: f["value"] for f in merged["fields"]}
    assert by_name == {"host": "new.local"}


def test_merge_handles_none_yaml_value() -> None:
    """D-31: None in YAML behaves identically to '' — preserve cluster value."""
    cur = _dc("qbit", fields=[{"name": "username", "value": "admin"}])
    des = _dc("qbit", fields=[{"name": "username", "value": None}])
    merged = merge_fields_for_put(cur, des)
    by_name = {f["name"]: f.get("value") for f in merged["fields"]}
    assert by_name == {"username": "admin"}


def test_merge_mixed_some_empty_some_not() -> None:
    """D-31: per-entry value-based rule — empties preserved, non-empties kept."""
    cur = _dc(
        "qbit",
        fields=[
            {"name": "host", "value": "qbit.local"},
            {"name": "password", "value": "***REDACTED***"},
        ],
    )
    des = _dc(
        "qbit",
        fields=[
            {"name": "host", "value": "qbit.local"},
            {"name": "password", "value": ""},
        ],
    )
    merged = merge_fields_for_put(cur, des)
    by_name = {f["name"]: f["value"] for f in merged["fields"]}
    assert by_name == {"host": "qbit.local", "password": "***REDACTED***"}


def test_merge_does_not_clobber_tags() -> None:
    """T-02.1-06: tags is auto-managed by reconciler — desired wins, current does not leak in."""
    cur = _dc("qbit", tags=[])
    des = _dc("qbit", tags=[1])
    merged = merge_fields_for_put(cur, des)
    assert merged["tags"] == [1]


def test_merge_when_cluster_field_missing() -> None:
    """Edge: desired field empty, cluster has no entry by that name — entry kept as-is."""
    cur = _dc("qbit", fields=[{"name": "host", "value": "qbit.local"}])
    des = _dc("qbit", fields=[{"name": "password", "value": ""}])
    merged = merge_fields_for_put(cur, des)
    # No cluster value to preserve from; entry stays empty (caller handles downstream)
    by_name = {f["name"]: f.get("value") for f in merged["fields"]}
    assert by_name == {"password": ""}
