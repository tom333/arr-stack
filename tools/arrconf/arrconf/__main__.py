"""arrconf CLI entrypoint — 4 subcommands per D-01..D-04 + REQ-cli-subcommands.

Exit code contract (CLAUDE.md CLI section):
    0 — success
    1 — application failure (e.g. upstream API error)
    2 — config error (parse / validation / missing API key)
    3 — drift detected by ``diff`` (only emitted by ``diff``)
"""

from __future__ import annotations

from pathlib import Path

import structlog
import typer

from arrconf.client_base import ProwlarrClient, RadarrClient, SonarrClient
from arrconf.config import load_config
from arrconf.diff_cmd import diff_prowlarr, diff_radarr, diff_sonarr
from arrconf.dump import dump_sonarr
from arrconf.exceptions import (
    ApiClientError,
    ConfigError,
    ReconcileError,
    ScopeViolationError,
)
from arrconf.logging import configure_logging
from arrconf.reconcilers.prowlarr import reconcile_prowlarr
from arrconf.reconcilers.radarr import reconcile_radarr
from arrconf.reconcilers.sonarr import reconcile_sonarr
from arrconf.schema_gen import write_schema
from arrconf.settings import Settings

app = typer.Typer(
    name="arrconf",
    help="Reconcile *arr app configurations from YAML to REST APIs.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,  # T-01-01: avoid leaking secrets in tracebacks
)


def _selected_apps(apps: str | None) -> set[str]:
    """Return the set of apps targeted by ``--apps``; defaults to all Phase-3 apps.

    Each branch in apply/dump/diff additionally guards on whether the app is
    present in the YAML (``"main" in root.<app>``), so the default of
    ``{sonarr, radarr, prowlarr}`` is safe — apps absent from the YAML
    simply skip silently.
    """
    if apps:
        return {a.strip() for a in apps.split(",")}
    return {"sonarr", "radarr", "prowlarr"}


@app.callback()
def main(
    ctx: typer.Context,
    config: Path = typer.Option(
        Path("/etc/arrconf/arrconf.yml"),
        "--config",
        "-c",
        help="Path to arrconf YAML config",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        "-l",
        envvar="ARRCONF_LOG_LEVEL",
    ),
) -> None:
    """Configure logging and stash common options for subcommands."""
    configure_logging(log_level)
    ctx.obj = {"config_path": config}


@app.command()
def apply(
    ctx: typer.Context,
    apps: str | None = typer.Option(None, help="Comma-separated apps"),
    dry_run: bool = typer.Option(False, "--dry-run", envvar="ARRCONF_DRY_RUN"),
) -> None:
    """Reconcile YAML → cluster APIs. Exit 0=ok, 1=app failure, 2=config error."""
    log = structlog.get_logger()
    try:
        root = load_config(ctx.obj["config_path"])
    except ConfigError as e:
        log.error("config_error", error=str(e))
        raise typer.Exit(code=2) from e
    except ScopeViolationError as e:
        log.error("scope_violation", error=str(e))
        raise typer.Exit(code=2) from e

    targets = _selected_apps(apps)
    settings = Settings()
    failures: list[str] = []

    if "sonarr" in targets and "main" in root.sonarr:
        instance = root.sonarr["main"]
        # Fast-fail when SONARR_API_KEY missing — no silent fallback to "" (CLAUDE.md
        # "no silent failures"). Symptom of the old fallback: 401 from upstream with
        # no clear hint that env was missing.
        if not settings.sonarr_api_key:
            log.error("missing_api_key", app="sonarr", env_var="SONARR_API_KEY")
            raise typer.Exit(code=2)
        api_key = settings.sonarr_api_key.get_secret_value()
        try:
            client = SonarrClient(base_url=instance.base_url, api_key=api_key)
            result = reconcile_sonarr(client, instance, dry_run=dry_run or settings.arrconf_dry_run)
            if all(
                a == "no-op" or a.startswith("prune-")
                for a in (p.action.value for p in result.plan)
            ):
                log.info("no-op", app="sonarr", count=len(result.plan))
            else:
                log.info("apply_complete", app="sonarr", actions=result.actions_taken)
        except (ApiClientError, ReconcileError) as e:
            log.error("app_failed", app="sonarr", error=str(e))
            failures.append("sonarr")

    # NEW: Radarr branch (Plan 06 wiring — D-03-01 full parity).
    if "radarr" in targets and "main" in root.radarr:
        radarr_instance = root.radarr["main"]
        if not settings.radarr_api_key:
            log.error("missing_api_key", app="radarr", env_var="RADARR_API_KEY")
            raise typer.Exit(code=2)
        radarr_api_key = settings.radarr_api_key.get_secret_value()
        try:
            radarr_client = RadarrClient(base_url=radarr_instance.base_url, api_key=radarr_api_key)
            radarr_result = reconcile_radarr(
                radarr_client, radarr_instance, dry_run=dry_run or settings.arrconf_dry_run
            )
            if all(
                a == "no-op" or a.startswith("prune-")
                for a in (p.action.value for p in radarr_result.plan)
            ):
                log.info("no-op", app="radarr", count=len(radarr_result.plan))
            else:
                log.info("apply_complete", app="radarr", actions=radarr_result.actions_taken)
        except (ApiClientError, ReconcileError) as e:
            log.error("app_failed", app="radarr", error=str(e))
            failures.append("radarr")

    # NEW: Prowlarr branch (Plan 06 wiring — D-03-02 app sync only).
    if "prowlarr" in targets and "main" in root.prowlarr:
        prowlarr_instance = root.prowlarr["main"]
        if not settings.prowlarr_api_key:
            log.error("missing_api_key", app="prowlarr", env_var="PROWLARR_API_KEY")
            raise typer.Exit(code=2)
        prowlarr_api_key = settings.prowlarr_api_key.get_secret_value()
        try:
            prowlarr_client = ProwlarrClient(
                base_url=prowlarr_instance.base_url, api_key=prowlarr_api_key
            )
            prowlarr_actions = reconcile_prowlarr(
                prowlarr_client, prowlarr_instance, dry_run=dry_run or settings.arrconf_dry_run
            )
            if not prowlarr_actions:
                log.info("no-op", app="prowlarr", count=len(prowlarr_instance.apps.items))
            else:
                log.info("apply_complete", app="prowlarr", actions=prowlarr_actions)
        except (ApiClientError, ReconcileError) as e:
            log.error("app_failed", app="prowlarr", error=str(e))
            failures.append("prowlarr")

    if failures:
        raise typer.Exit(code=1)
    raise typer.Exit(code=0)


@app.command()
def dump(
    ctx: typer.Context,
    apps: str | None = typer.Option(None, help="Comma-separated apps"),
    output: Path = typer.Option(
        Path("examples/baseline-sonarr.yml"),
        "--output",
        "-o",
        help="Output YAML path (relative to repo root)",
    ),
) -> None:
    """Read-only export of cluster state to YAML. Exit 0=ok, 1=app failure."""
    log = structlog.get_logger()
    targets = _selected_apps(apps)
    settings = Settings()
    try:
        root = load_config(ctx.obj["config_path"])
    except ConfigError as e:
        log.error("config_error", error=str(e))
        raise typer.Exit(code=2) from e
    if "sonarr" in targets and "main" in root.sonarr:
        instance = root.sonarr["main"]
        # Fast-fail when SONARR_API_KEY missing — mirrors the apply branch.
        if not settings.sonarr_api_key:
            log.error("missing_api_key", app="sonarr", env_var="SONARR_API_KEY")
            raise typer.Exit(code=2)
        api_key = settings.sonarr_api_key.get_secret_value()
        try:
            client = SonarrClient(base_url=instance.base_url, api_key=api_key)
            dump_sonarr(client, output)
            log.info("dump_written", path=str(output))
        except ApiClientError as e:
            log.error("app_failed", app="sonarr", error=str(e))
            raise typer.Exit(code=1) from e
    # dump is sonarr-only in Phase 3 (CONTEXT.md deferred stretch goal).
    for unsupported in targets - {"sonarr"}:
        if unsupported in ("radarr", "prowlarr"):
            log.warning(
                "dump_not_implemented",
                app=unsupported,
                hint="dump for radarr/prowlarr is deferred to a future phase (Phase 3 CONTEXT.md)",
            )
    raise typer.Exit(code=0)


@app.command()
def diff(
    ctx: typer.Context,
    apps: str | None = typer.Option(None, help="Comma-separated apps"),
) -> None:
    """Compare YAML vs cluster. Exit 0=no drift, 1=app failure, 2=config error, 3=drift."""
    log = structlog.get_logger()
    try:
        root = load_config(ctx.obj["config_path"])
    except ConfigError as e:
        log.error("config_error", error=str(e))
        raise typer.Exit(code=2) from e
    targets = _selected_apps(apps)
    settings = Settings()
    max_code = 0
    if "sonarr" in targets and "main" in root.sonarr:
        instance = root.sonarr["main"]
        # Fast-fail when SONARR_API_KEY missing — mirrors apply/dump branches.
        if not settings.sonarr_api_key:
            log.error("missing_api_key", app="sonarr", env_var="SONARR_API_KEY")
            raise typer.Exit(code=2)
        api_key = settings.sonarr_api_key.get_secret_value()
        try:
            client = SonarrClient(base_url=instance.base_url, api_key=api_key)
            code = diff_sonarr(client, root)
            max_code = max(max_code, code)
        except ApiClientError as e:
            log.error("app_failed", app="sonarr", error=str(e))
            raise typer.Exit(code=1) from e

    # NEW: Radarr diff.
    if "radarr" in targets and "main" in root.radarr:
        radarr_diff_instance = root.radarr["main"]
        if not settings.radarr_api_key:
            log.error("missing_api_key", app="radarr", env_var="RADARR_API_KEY")
            raise typer.Exit(code=2)
        radarr_diff_key = settings.radarr_api_key.get_secret_value()
        try:
            radarr_diff_client = RadarrClient(
                base_url=radarr_diff_instance.base_url, api_key=radarr_diff_key
            )
            code = diff_radarr(radarr_diff_client, root)
            max_code = max(max_code, code)
        except ApiClientError as e:
            log.error("app_failed", app="radarr", error=str(e))
            raise typer.Exit(code=1) from e

    # NEW: Prowlarr diff.
    if "prowlarr" in targets and "main" in root.prowlarr:
        prowlarr_diff_instance = root.prowlarr["main"]
        if not settings.prowlarr_api_key:
            log.error("missing_api_key", app="prowlarr", env_var="PROWLARR_API_KEY")
            raise typer.Exit(code=2)
        prowlarr_diff_key = settings.prowlarr_api_key.get_secret_value()
        try:
            prowlarr_diff_client = ProwlarrClient(
                base_url=prowlarr_diff_instance.base_url, api_key=prowlarr_diff_key
            )
            code = diff_prowlarr(prowlarr_diff_client, root)
            max_code = max(max_code, code)
        except (ApiClientError, ReconcileError) as e:
            log.error("app_failed", app="prowlarr", error=str(e))
            raise typer.Exit(code=1) from e

    raise typer.Exit(code=max_code)


@app.command(name="schema-gen")
def schema_gen_cmd(
    output: Path = typer.Option(
        Path("schemas/arrconf-schema.json"),
        "--output",
        "-o",
        help="Output JSON Schema path (D-15)",
    ),
) -> None:
    """Export JSON Schema (Draft 2020-12) from RootConfig (D-15)."""
    log = structlog.get_logger()
    output.parent.mkdir(parents=True, exist_ok=True)
    write_schema(output)
    log.info("schema_written", path=str(output))
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
