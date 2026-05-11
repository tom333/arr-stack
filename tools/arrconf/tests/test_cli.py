"""CLI smoke tests — typer subcommand wiring + exit codes (REQ-cli-subcommands)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from arrconf.__main__ import app

runner = CliRunner()


def test_help_lists_four_subcommands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ["apply", "dump", "diff", "schema-gen"]:
        assert cmd in result.stdout, f"Missing subcommand {cmd} in --help output"


def test_apply_help_shows_dry_run_flag() -> None:
    result = runner.invoke(app, ["apply", "--help"])
    assert result.exit_code == 0
    assert "--dry-run" in result.stdout
    assert "--apps" in result.stdout


def test_apply_missing_config_returns_exit_2(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--config", str(tmp_path / "missing.yml"), "apply"])
    assert result.exit_code == 2


def test_apply_missing_api_key_returns_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fast-fail when SONARR_API_KEY env is unset — exit 2 + missing_api_key log."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    download_clients:\n      prune: false\n      items: []\n"
    )
    monkeypatch.delenv("SONARR_API_KEY", raising=False)
    result = runner.invoke(app, ["--config", str(cfg), "apply"])
    assert result.exit_code == 2, (
        f"Expected exit 2 (missing api key), got {result.exit_code}: {result.stdout}"
    )
    assert "missing_api_key" in result.stdout, (
        f"Expected 'missing_api_key' in log output: {result.stdout}"
    )


def test_dump_missing_api_key_returns_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mirror of test_apply_missing_api_key for dump."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    download_clients:\n      prune: false\n      items: []\n"
    )
    monkeypatch.delenv("SONARR_API_KEY", raising=False)
    result = runner.invoke(
        app,
        [
            "--config",
            str(cfg),
            "dump",
            "--output",
            str(tmp_path / "out.yml"),
        ],
    )
    assert result.exit_code == 2
    assert "missing_api_key" in result.stdout


def test_diff_missing_api_key_returns_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mirror of test_apply_missing_api_key for diff."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    download_clients:\n      prune: false\n      items: []\n"
    )
    monkeypatch.delenv("SONARR_API_KEY", raising=False)
    result = runner.invoke(app, ["--config", str(cfg), "diff"])
    assert result.exit_code == 2
    assert "missing_api_key" in result.stdout


def test_diff_invalid_yaml_returns_exit_2(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yml"
    # `bogus: 99` is not in DownloadClientsSection schema (extra="forbid")
    bad.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    download_clients:\n      prune: false\n      bogus: 99\n"
    )
    result = runner.invoke(app, ["--config", str(bad), "diff"])
    assert result.exit_code == 2


def test_schema_gen_writes_draft_2020_12(tmp_path: Path) -> None:
    out = tmp_path / "schema.json"
    result = runner.invoke(app, ["schema-gen", "--output", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_apply_unknown_apps_returns_exit_2(tmp_path: Path) -> None:
    """CR-03 regression: typo in --apps must fail loud (exit 2), not silently skip.

    Pre-fix behaviour: ``--apps sonar`` returned ``{"sonar"}``, every branch in
    apply / dump / diff skipped because no guard matched, and the command
    exited 0 with no work done. Combined with the CronJob deployment model,
    that silently disabled all reconciliation on a typo. The fix validates
    against ``_VALID_APPS`` and raises ``typer.BadParameter`` (exit 2 — config
    error per CLAUDE.md CLI conventions).
    """
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    download_clients:\n      prune: false\n      items: []\n"
    )
    result = runner.invoke(app, ["--config", str(cfg), "apply", "--apps", "sonar"])
    assert result.exit_code == 2, (
        f"CR-03: --apps sonar must exit 2 (config error), got {result.exit_code}: {result.stdout!r}"
    )


def test_diff_unknown_apps_returns_exit_2(tmp_path: Path) -> None:
    """CR-03 regression: typo in --apps for diff also fails loud."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    download_clients:\n      prune: false\n      items: []\n"
    )
    result = runner.invoke(app, ["--config", str(cfg), "diff", "--apps", "radar"])
    assert result.exit_code == 2


def test_dump_unknown_apps_returns_exit_2(tmp_path: Path) -> None:
    """CR-03 regression: typo in --apps for dump also fails loud."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    download_clients:\n      prune: false\n      items: []\n"
    )
    result = runner.invoke(
        app,
        [
            "--config",
            str(cfg),
            "dump",
            "--output",
            str(tmp_path / "out.yml"),
            "--apps",
            "prowlar",
        ],
    )
    assert result.exit_code == 2


def test_diff_sonarr_catches_reconcile_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """WR-03 regression: diff sonarr branch must catch ReconcileError, not crash.

    Pre-fix, the diff branch only caught ApiClientError. A ReconcileError
    raised from a reconcile / diff helper would propagate as an unhandled
    exception and crash the CLI instead of returning the documented exit
    code 1.

    Patches diff_cmd.diff_sonarr to raise ReconcileError directly — the
    test is about the exception-handling contract in __main__.diff, not
    about which specific path can raise (the apply branch already catches
    both).
    """
    from arrconf.exceptions import ReconcileError as _ReconcileError

    def boom(*a, **k):  # noqa: ANN001, ANN002, ANN003, ANN202
        raise _ReconcileError("synthetic for WR-03 contract test")

    monkeypatch.setattr("arrconf.__main__.diff_sonarr", boom)

    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    download_clients:\n      prune: false\n      items: []\n"
    )
    monkeypatch.setenv("SONARR_API_KEY", "fake")
    result = runner.invoke(app, ["--config", str(cfg), "diff"])
    assert result.exit_code == 1, (
        f"WR-03: diff branch must catch ReconcileError and exit 1, got "
        f"{result.exit_code}: {result.stdout!r}"
    )
    assert "app_failed" in result.stdout


def test_diff_radarr_catches_reconcile_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """WR-03 regression: diff radarr branch must catch ReconcileError, not crash."""
    from arrconf.exceptions import ReconcileError as _ReconcileError

    def boom(*a, **k):  # noqa: ANN001, ANN002, ANN003, ANN202
        raise _ReconcileError("synthetic for WR-03 contract test")

    monkeypatch.setattr("arrconf.__main__.diff_radarr", boom)

    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "radarr:\n  main:\n    base_url: http://radarr.test\n"
        "    download_clients:\n      prune: false\n      items: []\n"
    )
    monkeypatch.setenv("RADARR_API_KEY", "fake")
    result = runner.invoke(app, ["--config", str(cfg), "diff", "--apps", "radarr"])
    assert result.exit_code == 1
    assert "app_failed" in result.stdout


def test_apply_known_apps_subset_accepted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CR-03 companion: valid subset (e.g. --apps sonarr,radarr) is accepted."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    download_clients:\n      prune: false\n      items: []\n"
    )
    # No SONARR_API_KEY → exit 2 from missing_api_key (not from CR-03 validation),
    # which still proves CR-03 validation accepted "sonarr,radarr":
    monkeypatch.delenv("SONARR_API_KEY", raising=False)
    result = runner.invoke(app, ["--config", str(cfg), "apply", "--apps", "sonarr,radarr"])
    assert result.exit_code == 2
    assert "missing_api_key" in result.stdout, (
        "validation must let known-apps subset through to api-key check; "
        f"got stdout: {result.stdout!r}"
    )


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_diff_returns_3_on_drift(
    respx_mock,  # noqa: ANN001
    tmp_path: Path,
    sonarr_tag_managed_fixture: list[dict],
    sonarr_downloadclient_fixture: list[dict],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """diff exits 3 when cluster state differs from YAML."""
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=sonarr_tag_managed_fixture))
    # Cluster has 1 client, YAML has 0 → PRUNE_SKIP (still drift, exit 3)
    respx_mock.get("/downloadclient").mock(
        return_value=httpx.Response(200, json=sonarr_downloadclient_fixture)
    )
    # Phase 3 extension: reconcile_sonarr also reads these endpoints.
    respx_mock.get("/indexer").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/rootfolder").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/notification").mock(return_value=httpx.Response(200, json=[]))
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    download_clients:\n      prune: false\n      items: []\n"
    )
    monkeypatch.setenv("SONARR_API_KEY", "fake")
    result = runner.invoke(app, ["--config", str(cfg), "diff"])
    assert result.exit_code == 3, (
        f"Expected exit code 3 (drift), got {result.exit_code}: {result.stdout}"
    )
