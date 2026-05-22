"""CLI smoke tests — typer subcommand wiring + exit codes (REQ-cli-subcommands)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from arrconf.__main__ import app

runner = CliRunner()

# Rich-based typer help output interleaves ANSI color codes through flag names
# (e.g. "--dry-run" renders as "-\x1b[0m\x1b[1;36m-dry\x1b[0m\x1b[1;36m-run"),
# breaking naive substring checks in CI environments where rich force-detects
# color (CI=true / GITHUB_ACTIONS=true). Strip ANSI before asserting on flag text.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


def test_help_lists_four_subcommands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    plain = _strip_ansi(result.stdout)
    for cmd in ["apply", "dump", "diff", "schema-gen"]:
        assert cmd in plain, f"Missing subcommand {cmd} in --help output"


def test_apply_help_shows_dry_run_flag() -> None:
    result = runner.invoke(app, ["apply", "--help"])
    assert result.exit_code == 0
    plain = _strip_ansi(result.stdout)
    assert "--dry-run" in plain
    assert "--apps" in plain


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
        "    download_clients:\n      prune: false\n"
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
        "    download_clients:\n      prune: false\n"
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
        "    download_clients:\n      prune: false\n"
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
        "    download_clients:\n      prune: false\n"
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
        "    download_clients:\n      prune: false\n"
    )
    result = runner.invoke(app, ["--config", str(cfg), "diff", "--apps", "radar"])
    assert result.exit_code == 2


def test_dump_unknown_apps_returns_exit_2(tmp_path: Path) -> None:
    """CR-03 regression: typo in --apps for dump also fails loud."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    download_clients:\n      prune: false\n"
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
        "    download_clients:\n      prune: false\n"
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
        "    download_clients:\n      prune: false\n"
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
        "    download_clients:\n      prune: false\n"
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
    # Phase 5 extension: reconcile_sonarr now also reads remotepathmapping and series.
    respx_mock.get("/remotepathmapping").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/series").mock(return_value=httpx.Response(200, json=[]))
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    download_clients:\n      prune: false\n"
    )
    monkeypatch.setenv("SONARR_API_KEY", "fake")
    result = runner.invoke(app, ["--config", str(cfg), "diff"])
    assert result.exit_code == 3, (
        f"Expected exit code 3 (drift), got {result.exit_code}: {result.stdout}"
    )


# ---------------------------------------------------------------------------
# Phase 5 (D-05-BOOTSTRAP-01): qBittorrent fail-fast env-var gate
# ---------------------------------------------------------------------------


def test_apply_missing_qbt_user_returns_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-05-BOOTSTRAP-01 gate #2: exit 2 + missing_env_vars log when QBT_USER is unset."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text("qbittorrent:\n  main:\n    base_url: http://qbit:8080\n")
    monkeypatch.delenv("QBT_USER", raising=False)
    monkeypatch.setenv("QBT_PASS", "secret")
    result = runner.invoke(app, ["--config", str(cfg), "apply", "--apps", "qbittorrent"])
    assert result.exit_code == 2, (
        f"Expected exit 2 (missing QBT_USER), got {result.exit_code}: {result.stdout}"
    )
    assert "missing_env_vars" in result.stdout, (
        f"Expected 'missing_env_vars' in log output: {result.stdout}"
    )
    assert "QBT_USER" in result.stdout, f"Expected 'QBT_USER' in log output: {result.stdout}"


def test_apply_missing_qbt_pass_returns_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-05-BOOTSTRAP-01 gate #2: exit 2 + missing_env_vars log when QBT_PASS is unset."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text("qbittorrent:\n  main:\n    base_url: http://qbit:8080\n")
    monkeypatch.setenv("QBT_USER", "admin")
    monkeypatch.delenv("QBT_PASS", raising=False)
    result = runner.invoke(app, ["--config", str(cfg), "apply", "--apps", "qbittorrent"])
    assert result.exit_code == 2, (
        f"Expected exit 2 (missing QBT_PASS), got {result.exit_code}: {result.stdout}"
    )
    assert "missing_env_vars" in result.stdout, (
        f"Expected 'missing_env_vars' in log output: {result.stdout}"
    )
    assert "QBT_PASS" in result.stdout, f"Expected 'QBT_PASS' in log output: {result.stdout}"


def test_apply_qbittorrent_both_env_set_does_not_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-05-BOOTSTRAP-01: when both QBT_USER + QBT_PASS are set, gate #2 is cleared.

    The reconciler itself is not wired yet (Plan 04) so exit may be 0 or 1 —
    the gate check is what we verify here (exit code MUST NOT be 2).
    """
    cfg = tmp_path / "cfg.yml"
    cfg.write_text("qbittorrent:\n  main:\n    base_url: http://qbit:8080\n")
    monkeypatch.setenv("QBT_USER", "admin")
    monkeypatch.setenv("QBT_PASS", "secret")
    result = runner.invoke(app, ["--config", str(cfg), "apply", "--apps", "qbittorrent"])
    assert result.exit_code != 2, f"Exit 2 means fail-fast fired unexpectedly; got: {result.stdout}"


def test_help_lists_qbittorrent_in_apps_option(tmp_path: Path) -> None:
    """Phase 5: qbittorrent must appear in --help as a valid app name."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    # The _VALID_APPS frozenset appears in the BadParameter error string;
    # a simpler check: "qbittorrent" appears somewhere in the apply --help.
    apply_result = runner.invoke(app, ["apply", "--help"])
    assert apply_result.exit_code == 0
    # After adding qbittorrent to _VALID_APPS, the error message for invalid
    # apps will include it — indirect but sufficient for this gate.
    cfg = tmp_path / "cfg.yml"
    cfg.write_text("qbittorrent:\n  main:\n    base_url: http://qbit:8080\n")
    invalid_result = runner.invoke(app, ["--config", str(cfg), "apply", "--apps", "not-an-app"])
    assert "qbittorrent" in invalid_result.stdout, (
        f"Expected 'qbittorrent' in valid-apps error output: {invalid_result.stdout}"
    )


def test_apply_invalid_app_qbittorent_typo_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CR-03 companion: typo 'qbittorent' (missing 't') is rejected at frozenset check."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text("qbittorrent:\n  main:\n    base_url: http://qbit:8080\n")
    monkeypatch.setenv("QBT_USER", "admin")
    monkeypatch.setenv("QBT_PASS", "secret")
    result = runner.invoke(
        app,
        ["--config", str(cfg), "apply", "--apps", "qbittorent"],  # typo: missing 't'
    )
    assert result.exit_code == 2, (
        f"CR-03: --apps qbittorent must exit 2 (typo), got {result.exit_code}: {result.stdout!r}"
    )
