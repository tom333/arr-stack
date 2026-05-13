"""Unit tests for arrconf.differ.reconcile() — covers all 6 Action cases + read-only diff."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from arrconf.differ import Action, diff_models, merge_fields_for_put, reconcile
from arrconf.resources.sonarr.download_client import DownloadClient, FieldKV


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


def test_diff_models_strips_production_api_mask() -> None:
    """WR-01 (Phase 3 code review): real production mask `"********"` must be stripped.

    Pre-fix, _strip_redacted_fields only matched the in-tree fixture sentinel
    `"***REDACTED***"`. Against a real Prowlarr cluster, the GET response carries
    `"********"` for `privacy="apiKey"` fields. Comparing that against desired
    (which carries the real resolved key) flagged `fields` as drifted on every
    cycle — every Prowlarr reconcile planned a spurious UPDATE. The fix extends
    the stripping to the frozenset `_API_MASK_VALUES = {"***REDACTED***", "********"}`.

    Contract: when the only difference between two models is that one side has an
    apiKey field with the production mask `"********"` and the other has it
    stripped (i.e. dump emitter's behaviour), diff_models returns NO drift on
    the `fields` axis. The test exercises both mask sentinels symmetrically.
    """
    cluster_with_production_mask = _dc(
        "qbit",
        fields=[FieldKV(name="apiKey", value="********", privacy="apiKey")],
    )
    cluster_with_in_tree_mask = _dc(
        "qbit",
        fields=[FieldKV(name="apiKey", value="***REDACTED***", privacy="apiKey")],
    )
    desired_with_real_key_stripped_by_dump = _dc("qbit", fields=[])
    # Both mask variants must compare-equal to a stripped-fields desired:
    assert "fields" not in diff_models(
        cluster_with_production_mask, desired_with_real_key_stripped_by_dump
    ), "WR-01: '********' production mask must be stripped before diff_models"
    assert "fields" not in diff_models(
        cluster_with_in_tree_mask, desired_with_real_key_stripped_by_dump
    ), "Existing contract: '***REDACTED***' fixture sentinel must continue to be stripped"


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


# --- v0.1.5 / D-02.2-AUTH-REGRESSION credential-mask omission contract -----------------
# APPENDED in Plan 02.2-07 (RED → Plan 02.2-08 GREEN). The tests above this divider are
# PRE-EXISTING (Phase 2.1 / Plan 02.2-02) and MUST NOT be modified. The 3 tests below
# are the v0.1.5 contract: merge_fields_for_put must OMIT privacy=password|userName
# entries from the merged PUT body (Sonarr preserves stored values via absence — safer
# than substituting the API mask "********"). See ADR-8.1 (Plan 09).

_FIXTURE_ROOT_V0_1_5 = Path(__file__).parent / "fixtures"


@pytest.fixture
def sonarr_dc_with_real_mask() -> dict[str, Any]:
    """Cluster GET response variant with the LITERAL production mask `"********"`.

    The in-tree fixture uses `***REDACTED***` (the test-redaction substitute),
    but the production cluster (forensic-credentials-diff-2026-05-09T0651.txt)
    shows the real Sonarr API mask is `"********"`. Both must be omitted by
    `merge_fields_for_put` after the v0.1.5 fix lands.
    """
    in_tree = json.loads((_FIXTURE_ROOT_V0_1_5 / "sonarr/downloadclient.json").read_text())
    payload: dict[str, Any] = in_tree[0]
    for f in payload["fields"]:
        if f.get("privacy") in ("password", "userName"):
            f["value"] = "********"
    return payload


def test_merge_fields_omits_privacy_password_when_value_is_api_mask(
    sonarr_dc_with_real_mask: dict[str, Any],
) -> None:
    """RED — D-02.2-AUTH-REGRESSION: merge_fields_for_put MUST omit entries
    whose CLUSTER-side privacy metadata is `password` or `userName`.

    Trigger: cluster's stored value (as returned by Sonarr's GET) is the API
    mask token `"********"`. If the merge helper substitutes that value into
    the PUT body, Sonarr (with `?forceSave=true`) writes the literal mask as
    the credential — overwriting the real password.

    Behavior (post-fix): the merged body's `fields[]` list MUST NOT contain
    ANY entry whose `name` is `password` or `username`. This test currently
    FAILS because `merge_fields_for_put` consults only `name` (D-31/D-32
    contract from Phase 2.1), not `privacy`. Plan 08 GREEN changes the helper
    to consult `cur_f.privacy` and skip entries whose privacy is in
    ("password", "userName").
    """
    current = DownloadClient.model_validate(sonarr_dc_with_real_mask)

    desired_payload = dict(sonarr_dc_with_real_mask)
    desired_payload["fields"] = [
        {"name": "host", "value": "qbittorrent.selfhost.svc.cluster.local"},
        {"name": "port", "value": 8080},
        {"name": "useSsl", "value": False},
        {"name": "urlBase", "value": ""},
        {"name": "username", "value": ""},
        {"name": "password", "value": ""},
        {"name": "tvCategory", "value": "sonarr"},
        {"name": "tvImportedCategory", "value": ""},
        {"name": "recentTvPriority", "value": 0},
        {"name": "olderTvPriority", "value": 0},
        {"name": "initialState", "value": 0},
        {"name": "sequentialOrder", "value": False},
        {"name": "firstAndLast", "value": False},
        {"name": "contentLayout", "value": 0},
    ]
    desired_payload["tags"] = [1]
    desired = DownloadClient.model_validate(desired_payload)

    merged_body = merge_fields_for_put(current, desired)

    field_names = {f["name"] for f in merged_body.get("fields", [])}
    assert "password" not in field_names, (
        "RED — privacy=password field must be OMITTED from PUT body, NOT "
        "substituted with cluster mask '********' (D-02.2-AUTH-REGRESSION)"
    )
    assert "username" not in field_names, (
        "RED — privacy=userName field must be OMITTED from PUT body, NOT "
        "substituted with cluster mask '********' (D-02.2-AUTH-REGRESSION)"
    )

    assert "host" in field_names
    assert "port" in field_names
    assert "tvCategory" in field_names

    for f in merged_body.get("fields", []):
        assert f.get("value") != "********", (
            f"RED — merged body field {f['name']} carries API mask '********' — "
            f"v0.1.5 fix must prevent ALL mask passthrough"
        )


def test_merge_fields_omits_privacy_password_when_value_is_in_tree_redacted_mask() -> None:
    """RED — same contract, but exercises the in-tree fixture's `***REDACTED***`
    substitute. Both equivalence-class members must be omitted. The fix must
    consult the CLUSTER-side `privacy` metadata, NOT match against a
    mask-alphabet — that's the architectural difference between Option A
    (omit by metadata, chosen) and Option B (mask-token detect, rejected).

    CRITICAL ordering invariant for Plan 08 (T-02.2-08-02): the omit-credential
    branch MUST come BEFORE the existing empty-value-substitute-cluster branch
    in the per-field loop. This test exercises a `cur_f.value="***REDACTED***"`
    case (a non-empty cluster value) — a wrong-order helper would substitute
    the redacted token THEN miss the omit branch, leaving "password" present
    in the merged body. This test catches that ordering failure.
    """
    in_tree = json.loads((_FIXTURE_ROOT_V0_1_5 / "sonarr/downloadclient.json").read_text())
    current = DownloadClient.model_validate(in_tree[0])

    desired_payload = dict(in_tree[0])
    desired_payload["fields"] = [
        {"name": "host", "value": "qbittorrent.selfhost.svc.cluster.local"},
        {"name": "port", "value": 8080},
        {"name": "useSsl", "value": False},
        {"name": "urlBase", "value": ""},
        {"name": "username", "value": ""},
        {"name": "password", "value": ""},
        {"name": "tvCategory", "value": "sonarr"},
        {"name": "tvImportedCategory", "value": ""},
        {"name": "recentTvPriority", "value": 0},
        {"name": "olderTvPriority", "value": 0},
        {"name": "initialState", "value": 0},
        {"name": "sequentialOrder", "value": False},
        {"name": "firstAndLast", "value": False},
        {"name": "contentLayout", "value": 0},
    ]
    desired_payload["tags"] = [1]
    desired = DownloadClient.model_validate(desired_payload)

    merged_body = merge_fields_for_put(current, desired)

    field_names = {f["name"] for f in merged_body.get("fields", [])}
    assert "password" not in field_names, (
        "RED — privacy=password (in-tree '***REDACTED***') must be OMITTED"
    )
    assert "username" not in field_names, (
        "RED — privacy=userName (in-tree 'admin') must be OMITTED. "
        "Note: cluster's 'admin' is technically a real value, NOT a mask, "
        "but the omit-by-privacy-metadata strategy treats ALL credential "
        "fields uniformly — the absence-as-protection is the contract."
    )


def test_merge_fields_preserves_non_credential_empty_yaml_passthrough() -> None:
    """Sanity (PASSING regression-guard) — the v0.1.5 fix MUST NOT regress
    D-31/D-32 for non-credential fields. Empty YAML value + non-credential
    cluster value still triggers the merge_field_preserved substitution.

    Example: cluster.fields[name=tvCategory, value="sonarr",
    privacy="normal"] + desired.fields[name=tvCategory, value=""] →
    merged body MUST carry tvCategory=sonarr (not omit it). This is the
    existing Phase 2.1 contract from `test_merge_preserves_cluster_value_when_yaml_empty`
    but at a different angle (with explicit privacy=normal on the cluster
    side); Plan 08 must preserve it.
    """
    cluster_payload: dict[str, Any] = {
        "id": 1,
        "name": "qBittorrent",
        "enable": True,
        "protocol": "torrent",
        "priority": 1,
        "implementation": "QBittorrent",
        "configContract": "QBittorrentSettings",
        "fields": [
            {"name": "host", "value": "qb.local", "privacy": "normal"},
            {"name": "tvCategory", "value": "sonarr", "privacy": "normal"},
        ],
        "tags": [1],
        "removeCompletedDownloads": True,
        "removeFailedDownloads": True,
    }
    desired_payload = dict(cluster_payload)
    desired_payload["fields"] = [
        {"name": "host", "value": ""},
        {"name": "tvCategory", "value": ""},
    ]
    current = DownloadClient.model_validate(cluster_payload)
    desired = DownloadClient.model_validate(desired_payload)

    merged_body = merge_fields_for_put(current, desired)
    merged_by_name = {f["name"]: f for f in merged_body["fields"]}

    assert "host" in merged_by_name, "non-credential merge_field_preserved still required"
    assert merged_by_name["host"]["value"] == "qb.local"
    assert "tvCategory" in merged_by_name
    assert merged_by_name["tvCategory"]["value"] == "sonarr"


def test_merge_field_omitted_credential_event_payload_excludes_value(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """T-02.2-08-01: event payload is metadata-only ({name, privacy}). The
    credential VALUE must NEVER appear in the structlog output — even though
    the value is the API mask ``"********"`` (no real credential is exposed),
    the discipline is "no credential values in logs, ever."

    structlog is configured (``arrconf/logging.py``) to write to stdout via
    PrintLogger (JSON when non-TTY, ConsoleRenderer when TTY). pytest's
    ``capsys`` is the right primitive for this guard — ``caplog`` only sees
    stdlib ``logging`` records, which structlog does not emit by default.
    """
    in_tree = json.loads((_FIXTURE_ROOT_V0_1_5 / "sonarr/downloadclient.json").read_text())
    current = DownloadClient.model_validate(in_tree[0])

    desired_payload = dict(in_tree[0])
    desired_payload["fields"] = [
        {"name": "host", "value": "qb.local"},
        {"name": "username", "value": ""},
        {"name": "password", "value": ""},
    ]
    desired_payload["tags"] = [1]
    desired = DownloadClient.model_validate(desired_payload)

    merge_fields_for_put(current, desired)

    captured = capsys.readouterr()
    combined = captured.out + captured.err

    # At least 2 events emitted (one for username, one for password).
    omit_count = combined.count("merge_field_omitted_credential")
    assert omit_count >= 2, (
        f"Expected >=2 merge_field_omitted_credential events in log output, "
        f"got {omit_count}. Captured:\n{combined}"
    )

    # No credential value, mask token, or redaction sentinel must appear in logs.
    assert "********" not in combined, f"API mask leaked into log output: {combined}"
    assert "***REDACTED***" not in combined, f"Redacted token leaked into log output: {combined}"
    # Defensive: the literal cluster username "admin" must not flow either.
    # Match it as a token to avoid false positives on substrings like 'administrator'.
    for line in combined.splitlines():
        if "merge_field_omitted_credential" in line:
            assert "value=admin" not in line, f"username value leaked: {line}"
            assert '"value": "admin"' not in line, f"username value leaked: {line}"
            assert '"value":"admin"' not in line, f"username value leaked: {line}"


def test_merge_fields_passes_through_non_empty_credential_value_for_rotation() -> None:
    """Non-empty YAML credential must reach the PUT body (user intends rotation).

    CR-01 gap closure (VERIFICATION.md Truth #10): the omit-credential branch
    must NOT fire when desired value is non-empty. diff_models plans an UPDATE
    because the values differ; merge_fields_for_put must honour that intent by
    passing the field through so Sonarr applies the credential change.

    Contrast with test_merge_fields_omits_privacy_password_when_value_is_api_mask:
    that test uses desired value='' (empty placeholder) — the omit branch fires
    correctly. This test uses desired value='new_value' — the omit branch must
    NOT fire.
    """
    cur = _dc(
        "qBit",
        fields=[FieldKV(name="password", value="old_stored", privacy="password")],
    )
    des = _dc(
        "qBit",
        fields=[FieldKV(name="password", value="new_value", privacy="password")],
    )
    result = merge_fields_for_put(cur, des)
    fields_by_name = {f["name"]: f for f in result["fields"]}
    assert "password" in fields_by_name, (
        "Non-empty credential must NOT be omitted — user intends rotation (CR-01)"
    )
    assert fields_by_name["password"]["value"] == "new_value"


def test_merge_fields_omits_api_key_privacy_field() -> None:
    """WR-01: apiKey privacy -> omitted from PUT body when desired is empty.

    Phase 3 indexer reconcilers and Prowlarr app-sync reconcilers rely on this
    behavior — without it, ?forceSave=true would write the API mask
    "***REDACTED***" as the literal API key (the v0.1.4 regression class
    extended to apiKey privacy fields).
    """
    cur = _dc(
        "sonarr-indexer",
        fields=[FieldKV(name="apiKey", value="***REDACTED***", privacy="apiKey")],
    )
    des = _dc(
        "sonarr-indexer",
        fields=[FieldKV(name="apiKey", value="", privacy="apiKey")],
    )
    result = merge_fields_for_put(cur, des)
    field_names = {f["name"] for f in result["fields"]}
    assert "apiKey" not in field_names, (
        "WR-01: privacy=apiKey field must be OMITTED from PUT body when desired value is empty"
    )


def test_merge_fields_does_not_inject_empty_fields_for_models_without_fields() -> None:
    """WR-06 regression: HostConfig has no fields attribute — PUT body must NOT carry 'fields': [].

    Pre-fix, merge_fields_for_put's last statement unconditionally set
    des_dump['fields'] = merged_fields, so HostConfig (no fields[] attribute)
    ended up with des_dump['fields'] = [] in the PUT body. The endpoint likely
    ignored it, but it polluted audit logs and risked regressing on a future
    API version that validates payloads strictly.
    """
    from arrconf.resources.sonarr.host_config import HostConfig

    current = HostConfig(instanceName="Sonarr")
    desired = HostConfig(instanceName="SonarrRenamed")
    body = merge_fields_for_put(current, desired)
    assert "fields" not in body, (
        "WR-06: merge_fields_for_put must NOT inject empty 'fields': [] for models "
        f"that have no fields attribute — got body keys: {sorted(body.keys())}"
    )


def test_merge_fields_omits_token_privacy_field() -> None:
    """WR-01: token privacy -> omitted from PUT body when desired is empty.

    Notifications (webhook tokens) and any future *arr resource using
    privacy="token" must benefit from the same omit-by-metadata strategy
    that protects password / userName / apiKey.
    """
    cur = _dc(
        "webhook-notif",
        fields=[FieldKV(name="token", value="***REDACTED***", privacy="token")],
    )
    des = _dc(
        "webhook-notif",
        fields=[FieldKV(name="token", value="", privacy="token")],
    )
    result = merge_fields_for_put(cur, des)
    field_names = {f["name"] for f in result["fields"]}
    assert "token" not in field_names, (
        "WR-01: privacy=token field must be OMITTED from PUT body when desired value is empty"
    )
