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
