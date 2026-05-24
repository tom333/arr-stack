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

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from arrconf.client_base import SonarrClient
from arrconf.config import DownloadClientsSection, SonarrInstance
from arrconf.differ import Action
from arrconf.exceptions import ConfigError
from arrconf.generators.categories import SonarrDerived
from arrconf.reconcilers._shared import _resolve_qbit_credentials_from_env
from arrconf.reconcilers.sonarr import reconcile_sonarr
from arrconf.resources.sonarr.download_client import DownloadClient, FieldKV


def _build_qbit_dc(
    name: str = "qBittorrent-tv",
    *,
    username: str = "",
    password: str = "",
) -> DownloadClient:
    """Build a qBit DownloadClient mirroring the generator's output shape."""
    return DownloadClient(
        name=name,
        protocol="torrent",
        implementation="QBittorrent",
        configContract="QBittorrentSettings",
        fields=[
            FieldKV(name="host", value="qbittorrent.selfhost.svc.cluster.local"),
            FieldKV(name="port", value=8080),
            FieldKV(name="useSsl", value=False),
            FieldKV(name="urlBase", value=""),
            FieldKV(name="username", value=username),
            FieldKV(name="password", value=password),
            FieldKV(name="tvCategory", value="sonarr-tv"),
        ],
    )


def _field_value(dc: DownloadClient, name: str) -> Any:
    for f in dc.fields:
        if f.name == name:
            return f.value
    raise KeyError(f"field {name!r} not found in {dc.name!r}")


def test_yaml_empty_env_set_uses_env_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """SC#2 case (a): empty YAML + env set → env values flow into fields[]."""
    monkeypatch.setenv("QBT_USER", "qbituser")
    monkeypatch.setenv("QBT_PASS", "qbitpass")

    dc = _build_qbit_dc(username="", password="")
    resolved = _resolve_qbit_credentials_from_env([dc])

    assert len(resolved) == 1
    out = resolved[0]
    assert _field_value(out, "username") == "qbituser"
    assert _field_value(out, "password") == "qbitpass"
    assert _field_value(out, "host") == "qbittorrent.selfhost.svc.cluster.local"

    # Input DC must not have been mutated (model_copy returns new instance).
    assert _field_value(dc, "username") == ""
    assert _field_value(dc, "password") == ""


def test_yaml_explicit_env_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """SC#2 case (b): explicit YAML + env set → YAML wins, env values ignored."""
    monkeypatch.setenv("QBT_USER", "should-not-be-used")
    monkeypatch.setenv("QBT_PASS", "should-not-be-used")

    dc = _build_qbit_dc(username="explicit-user", password="explicit-pass")
    resolved = _resolve_qbit_credentials_from_env([dc])

    assert len(resolved) == 1
    out = resolved[0]
    assert _field_value(out, "username") == "explicit-user"
    assert _field_value(out, "password") == "explicit-pass"


def test_yaml_partial_username_explicit_password_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SC#2 case (c): YAML username explicit + password empty + QBT_PASS env set
    → username from YAML, password from env."""
    monkeypatch.setenv("QBT_USER", "ignored-because-yaml-explicit")
    monkeypatch.setenv("QBT_PASS", "from-env")

    dc = _build_qbit_dc(username="explicit-user", password="")
    resolved = _resolve_qbit_credentials_from_env([dc])

    out = resolved[0]
    assert _field_value(out, "username") == "explicit-user"
    assert _field_value(out, "password") == "from-env"


def test_non_qbit_dc_passes_through_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WR-01: helper must be a no-op for DCs whose implementation != 'QBittorrent'.

    Pre-fix, the helper iterated all DCs and matched fields by name regardless
    of implementation. FieldKV.extra='allow' means any DC could carry
    username/password fields[]; a future generator emitting a Transmission /
    SABnzbd DC would silently get QBT_USER/QBT_PASS injected. Gate on
    implementation to scope the substitution to qBit only.
    """
    monkeypatch.setenv("QBT_USER", "qbituser")
    monkeypatch.setenv("QBT_PASS", "qbitpass")

    # Build a non-qBit DC that happens to have username/password fields[]
    # (a Transmission DC would have these). The helper must NOT substitute.
    transmission_dc = DownloadClient(
        name="Transmission-tv",
        protocol="torrent",
        implementation="Transmission",
        configContract="TransmissionSettings",
        fields=[
            FieldKV(name="host", value="transmission.svc"),
            FieldKV(name="username", value=""),
            FieldKV(name="password", value=""),
        ],
    )

    resolved = _resolve_qbit_credentials_from_env([transmission_dc])

    # Non-qBit DC must pass through with username/password still empty —
    # NOT "qbituser"/"qbitpass" from env.
    assert len(resolved) == 1
    out = resolved[0]
    assert _field_value(out, "username") == "", (
        "WR-01: non-qBit DC must NOT receive QBT_USER injection"
    )
    assert _field_value(out, "password") == "", (
        "WR-01: non-qBit DC must NOT receive QBT_PASS injection"
    )
    # And the DC instance is returned as-is (no model_copy churn).
    assert out is transmission_dc


def test_yaml_empty_env_unset_raises_config_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-18-FAIL-FAST-01: empty YAML + unset env → ConfigError naming the DC entry.

    Asserts the exact substring format pinned in CONTEXT.md so the operator can
    grep `kubectl logs` for it.
    """
    monkeypatch.delenv("QBT_USER", raising=False)
    monkeypatch.delenv("QBT_PASS", raising=False)

    dc = _build_qbit_dc(name="qBittorrent-tv", username="", password="")

    with pytest.raises(ConfigError) as exc_info:
        _resolve_qbit_credentials_from_env([dc])

    msg = str(exc_info.value)
    assert "download_client 'qBittorrent-tv'" in msg
    assert "username is empty in YAML AND QBT_USER env is unset/empty" in msg


def _qbit_cluster_dc_payload() -> dict[str, Any]:
    """Cluster-side DC payload mirroring a real Sonarr GET /downloadclient response.

    Critical for SC#3: ``username`` carries ``privacy="userName"`` and ``password``
    carries ``privacy="password"`` UI metadata + the masked ``"********"`` value.
    The differ's ``_credential_field_names`` helper picks these names off the
    cluster side and ``_strip_redacted_fields`` removes them from BOTH sides of
    the diff comparison — so the env-injected desired value never produces a
    spurious UPDATE.
    """
    return {
        "id": 1,
        "name": "qBittorrent-tv",
        "enable": True,
        "protocol": "torrent",
        "implementation": "QBittorrent",
        "implementationName": "qBittorrent",
        "configContract": "QBittorrentSettings",
        "priority": 1,
        "removeCompletedDownloads": True,
        "removeFailedDownloads": True,
        "tags": [1],
        "fields": [
            {
                "name": "host",
                "value": "qbittorrent.selfhost.svc.cluster.local",
                "privacy": "normal",
            },
            {"name": "port", "value": 8080, "privacy": "normal"},
            {"name": "useSsl", "value": False, "privacy": "normal"},
            {"name": "urlBase", "value": "", "privacy": "normal"},
            {"name": "username", "value": "********", "privacy": "userName"},
            {"name": "password", "value": "********", "privacy": "password"},
            {"name": "tvCategory", "value": "sonarr-tv", "privacy": "normal"},
        ],
    }


def _managed_tag_payload() -> list[dict[str, Any]]:
    return [{"id": 1, "label": "arrconf-managed"}]


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_second_apply_zero_drift_on_download_clients_with_env_injected_creds(
    monkeypatch: pytest.MonkeyPatch,
    respx_mock: respx.MockRouter,
) -> None:
    """SC#3 idempotence (dispositive): a 2nd ``arrconf apply`` cycle with
    env-injected credentials produces 0 plan_action on download_clients.

    Setup:
      - QBT_USER / QBT_PASS env vars set (simulating cluster runtime).
      - Cluster GET returns a DC whose username/password carry the API mask
        ``"********"`` and ``privacy="userName"``/``privacy="password"`` metadata.
      - Desired DC (post-Phase-18 helper) carries the real env-injected values
        for username/password.

    Expected: ``differ.diff_models`` symmetrically strips credential-name fields
    on both sides via ``_credential_field_names`` + ``_strip_redacted_fields``,
    so the diff sees no drift — Action.NO_OP for that DC, no PUT call, 0
    plan_action.
    """
    monkeypatch.setenv("QBT_USER", "qbituser")
    monkeypatch.setenv("QBT_PASS", "qbitpass")

    cluster_dc = _qbit_cluster_dc_payload()
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=_managed_tag_payload()))
    respx_mock.get("/indexer").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/rootfolder").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=[cluster_dc]))
    respx_mock.get("/notification").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/remotepathmapping").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/series").mock(return_value=httpx.Response(200, json=[]))

    post_route = respx_mock.post("/downloadclient")
    put_route = respx_mock.put(
        url__regex=r"^http://sonarr\.test/api/v3/downloadclient/\d+(?:\?.*)?$"
    )
    delete_route = respx_mock.delete(url__regex=r"^http://sonarr\.test/api/v3/downloadclient/\d+$")

    # Build the desired DC the same way the generator emits it (empty creds) —
    # then run through the Phase 18 reconciler wiring (sonarr.py) end-to-end.
    desired_dc = _build_qbit_dc(name="qBittorrent-tv", username="", password="")
    # The reconciler stamps the managed tag onto desired before diffing (D-02).
    # Pre-stamp here so the round-trip property holds (cluster has tags=[1]).
    desired_dc = desired_dc.model_copy(update={"tags": [1]})

    instance = SonarrInstance(
        base_url="http://sonarr.test",
        download_clients=DownloadClientsSection(prune=False),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=[desired_dc],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

    # No add/update/delete on download_clients.
    assert post_route.call_count == 0, "2nd apply must not POST a new DC"
    assert put_route.call_count == 0, (
        "2nd apply with env-injected creds must not PUT — merge_fields_for_put + "
        "_strip_redacted_fields must absorb the cluster-mask vs env-value delta "
        "(SC#3 dispositive)"
    )
    assert delete_route.call_count == 0, "2nd apply must not DELETE the existing DC"

    # And the planner agrees: every planned action on the existing DC is NO_OP.
    actions_for_qbit = [
        p.action
        for p in result.plan
        if p.desired is not None and p.desired.name == "qBittorrent-tv"
    ]
    assert actions_for_qbit == [Action.NO_OP], (
        f"expected NO_OP for qBittorrent-tv, got {actions_for_qbit}"
    )
