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

from arrconf.client_base import JellyfinClient, ProwlarrClient, RadarrClient, SonarrClient
from arrconf.config import load_config
from arrconf.diff_cmd import diff_jellyfin, diff_prowlarr, diff_radarr, diff_sonarr
from arrconf.dump import dump_jellyfin, dump_sonarr
from arrconf.exceptions import (
    ApiClientError,
    ConfigError,
    ReconcileError,
    ScopeViolationError,
)
from arrconf.generators.categories import generate_qbit_categories
from arrconf.logging import configure_logging
from arrconf.reconcilers._shared import merge_with_manual
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


_VALID_APPS: frozenset[str] = frozenset(
    {"sonarr", "radarr", "prowlarr", "qbittorrent", "seerr", "jellyfin"}
)


def _selected_apps(apps: str | None) -> set[str]:
    """Return the set of apps targeted by ``--apps``; defaults to all Phase-3 apps.

    Each branch in apply/dump/diff additionally guards on whether the app is
    present in the YAML (``"main" in root.<app>``), so the default of
    ``{sonarr, radarr, prowlarr}`` is safe — apps absent from the YAML
    simply skip silently.

    CR-03 (Phase 3 code review): unknown app names raise ``typer.BadParameter``
    (which typer translates to exit code 2 — config error per CLAUDE.md CLI
    conventions). A typo like ``--apps sonar`` would otherwise silently skip
    every branch and exit 0 with no work done — invisible disable of all
    reconciliation in a CronJob context.
    """
    log = structlog.get_logger()
    if not apps:
        return set(_VALID_APPS)
    selected = {a.strip() for a in apps.split(",") if a.strip()}
    unknown = selected - _VALID_APPS
    if unknown:
        # Emit a structured log first so CronJob log pipelines can ingest the
        # validation failure with the same key shape as other config errors.
        log.error(
            "unknown_apps",
            unknown=sorted(unknown),
            valid=sorted(_VALID_APPS),
        )
        raise typer.BadParameter(
            f"unknown app(s): {sorted(unknown)} — valid: {sorted(_VALID_APPS)}"
        )
    return selected


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
            prowlarr_result = reconcile_prowlarr(
                prowlarr_client, prowlarr_instance, dry_run=dry_run or settings.arrconf_dry_run
            )
            # CR-02 (Phase 3 code review): reconcile_prowlarr now returns ProwlarrResult
            # (plan + actions_taken). The apply branch logs based on actions_taken, which
            # is empty in dry-run; that's correct here (apply is non-dry by default and
            # the dry-run path emits per-action structlog events from _execute).
            if not prowlarr_result.actions_taken:
                log.info("no-op", app="prowlarr", count=len(prowlarr_instance.apps.items))
            else:
                log.info("apply_complete", app="prowlarr", actions=prowlarr_result.actions_taken)
        except (ApiClientError, ReconcileError) as e:
            log.error("app_failed", app="prowlarr", error=str(e))
            failures.append("prowlarr")

    # Phase 5: qBittorrent branch (D-05-QBT-01, D-05-BOOTSTRAP-01 gate #2).
    if "qbittorrent" in targets and "main" in root.qbittorrent:
        # D-05-BOOTSTRAP-01 gate #2: fail-fast before constructing the client.
        # A future CronJob run on a degraded Secret exits with code 2 + structured
        # log event so on-call can identify the missing env vars without digging
        # into the full log stream.
        missing = [
            k
            for k, v in (("QBT_USER", settings.qbt_user), ("QBT_PASS", settings.qbt_pass))
            if not v
        ]
        if missing:
            log.error("missing_env_vars", app="qbittorrent", missing=missing)
            raise typer.Exit(code=2)
        try:
            # Lazy imports — reconcile_qbittorrent wired in Plan 04.
            # QbittorrentClient has a Plan 02 stub in client_base.py that
            # raises NotImplementedError until Plan 04 lands the real impl.
            from arrconf.client_base import QbittorrentClient  # noqa: PLC0415
            from arrconf.reconcilers.qbittorrent import (  # noqa: PLC0415
                reconcile_qbittorrent,
            )

            qbit_instance = root.qbittorrent["main"]
            # Phase 10 pre-merge (D-01/D-02): Categories->qBit categories.
            # When instance.categories.items is empty, use Categories-derived
            # list. When non-empty, manual section wins entirely (merge_with_manual).
            qbit_generated = generate_qbit_categories(root)
            qbit_instance.categories.items = merge_with_manual(
                qbit_instance.categories.items,
                qbit_generated,
                app="qbittorrent",
                resource="categories",
            )
            assert settings.qbt_user is not None and settings.qbt_pass is not None
            qbit_client = QbittorrentClient(
                base_url=qbit_instance.base_url,
                username=settings.qbt_user.get_secret_value(),
                password=settings.qbt_pass.get_secret_value(),
            )
            qbit_result = reconcile_qbittorrent(
                qbit_client, qbit_instance, dry_run=dry_run or settings.arrconf_dry_run
            )
            if not qbit_result.actions_taken:
                log.info("no-op", app="qbittorrent")
            else:
                log.info("apply_complete", app="qbittorrent", actions=qbit_result.actions_taken)
        except ImportError as e:
            log.error(
                "qbittorrent_reconciler_not_wired",
                error=str(e),
                hint=(
                    "Plan 04 (qbittorrent reconciler) must be merged"
                    " before --apps qbittorrent works"
                ),
            )
            failures.append("qbittorrent")
        except (ApiClientError, ReconcileError) as e:
            log.error("app_failed", app="qbittorrent", error=str(e))
            failures.append("qbittorrent")

    # Phase 6: Seerr branch (D-06-SCOPE-01, D-06-AUTH-01, REQ-app-coverage).
    if "seerr" in targets and "main" in root.seerr:
        if not settings.seerr_api_key:
            log.error("missing_api_key", app="seerr", env_var="SEERR_API_KEY")
            raise typer.Exit(code=2)
        try:
            from arrconf.client_base import SeerrClient  # noqa: PLC0415
            from arrconf.reconcilers.seerr import reconcile_seerr  # noqa: PLC0415

            seerr_instance = root.seerr["main"]
            seerr_api_key = settings.seerr_api_key.get_secret_value()
            seerr_client = SeerrClient(
                base_url=seerr_instance.base_url,
                api_key=seerr_api_key,
            )
            seerr_result = reconcile_seerr(
                seerr_client, seerr_instance, dry_run=dry_run or settings.arrconf_dry_run
            )
            if not seerr_result.actions_taken:
                log.info("no-op", app="seerr")
            else:
                log.info("apply_complete", app="seerr", actions=seerr_result.actions_taken)
        except (ApiClientError, ReconcileError) as e:
            log.error("app_failed", app="seerr", error=str(e))
            failures.append("seerr")

    # Phase 7: Jellyfin branch (D-07-INSTANCE-01, D-07-AUTH-01, REQ-app-coverage).
    if "jellyfin" in targets and "main" in root.jellyfin:
        if not settings.jellyfin_api_key:
            log.error("missing_api_key", app="jellyfin", env_var="JELLYFIN_API_KEY")
            raise typer.Exit(code=2)
        try:
            from arrconf.client_base import JellyfinClient  # noqa: PLC0415
            from arrconf.reconcilers.jellyfin import reconcile_jellyfin  # noqa: PLC0415

            jellyfin_instance = root.jellyfin["main"]
            jellyfin_api_key = settings.jellyfin_api_key.get_secret_value()
            jellyfin_client = JellyfinClient(
                base_url=jellyfin_instance.base_url,
                api_key=jellyfin_api_key,
            )
            jellyfin_result = reconcile_jellyfin(
                jellyfin_client, jellyfin_instance, dry_run=dry_run or settings.arrconf_dry_run
            )
            if not jellyfin_result.actions_taken:
                log.info("no-op", app="jellyfin")
            else:
                log.info("apply_complete", app="jellyfin", actions=jellyfin_result.actions_taken)
        except (ApiClientError, ReconcileError) as e:
            log.error("app_failed", app="jellyfin", error=str(e))
            failures.append("jellyfin")

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
    # Phase 7: Jellyfin dump (D-07-INSTANCE-01, REQ-app-coverage, SC#4 feeder).
    if "jellyfin" in targets and "main" in root.jellyfin:
        jellyfin_dump_instance = root.jellyfin["main"]
        if not settings.jellyfin_api_key:
            log.error("missing_api_key", app="jellyfin", env_var="JELLYFIN_API_KEY")
            raise typer.Exit(code=2)
        jellyfin_dump_key = settings.jellyfin_api_key.get_secret_value()
        try:
            jellyfin_dump_client = JellyfinClient(
                base_url=jellyfin_dump_instance.base_url,
                api_key=jellyfin_dump_key,
            )
            dump_jellyfin(jellyfin_dump_client, output)
            log.info("dump_written", app="jellyfin", path=str(output))
        except ApiClientError as e:
            log.error("app_failed", app="jellyfin", error=str(e))
            raise typer.Exit(code=1) from e

    # dump is sonarr+jellyfin in Phase 7 (CONTEXT.md deferred stretch goal for radarr/prowlarr).
    for unsupported in targets - {"sonarr", "jellyfin"}:
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
        # WR-03 (Phase 3 code review): also catch ReconcileError — _reconcile_host_config
        # can raise "host_config GET returned no id ..." and the apply branch already
        # catches both. Without this, the diff CLI would crash with an unhandled
        # exception instead of the documented exit code 1.
        except (ApiClientError, ReconcileError) as e:
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
        # WR-03: mirror Sonarr branch — _reconcile_host_config can raise ReconcileError.
        except (ApiClientError, ReconcileError) as e:
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

    # Phase 5: qBittorrent diff branch — same fail-fast gate as apply.
    if "qbittorrent" in targets and "main" in root.qbittorrent:
        missing = [
            k
            for k, v in (("QBT_USER", settings.qbt_user), ("QBT_PASS", settings.qbt_pass))
            if not v
        ]
        if missing:
            log.error("missing_env_vars", app="qbittorrent", missing=missing)
            raise typer.Exit(code=2)
        try:
            from arrconf.client_base import QbittorrentClient  # noqa: PLC0415
            from arrconf.diff_cmd import diff_qbittorrent  # noqa: PLC0415

            qbit_diff_instance = root.qbittorrent["main"]
            # Phase 10 pre-merge (Pitfall 5): diff must use the same merged shape
            # as apply to avoid false drift between the two commands.
            qbit_diff_generated = generate_qbit_categories(root)
            qbit_diff_instance.categories.items = merge_with_manual(
                qbit_diff_instance.categories.items,
                qbit_diff_generated,
                app="qbittorrent",
                resource="categories",
            )
            assert settings.qbt_user is not None and settings.qbt_pass is not None
            qbit_diff_client = QbittorrentClient(
                base_url=qbit_diff_instance.base_url,
                username=settings.qbt_user.get_secret_value(),
                password=settings.qbt_pass.get_secret_value(),
            )
            code = diff_qbittorrent(qbit_diff_client, root)
            max_code = max(max_code, code)
        except ImportError as e:
            log.error(
                "qbittorrent_diff_not_wired",
                error=str(e),
                hint="Plan 04 (qbittorrent reconciler + diff) must be merged first",
            )
            raise typer.Exit(code=1) from e
        except (ApiClientError, ReconcileError) as e:
            log.error("app_failed", app="qbittorrent", error=str(e))
            raise typer.Exit(code=1) from e

    # Phase 7: Jellyfin diff branch (D-07-INSTANCE-01, SC#4 dispositive).
    if "jellyfin" in targets and "main" in root.jellyfin:
        jellyfin_diff_instance = root.jellyfin["main"]
        if not settings.jellyfin_api_key:
            log.error("missing_api_key", app="jellyfin", env_var="JELLYFIN_API_KEY")
            raise typer.Exit(code=2)
        jellyfin_diff_key = settings.jellyfin_api_key.get_secret_value()
        try:
            jellyfin_diff_client = JellyfinClient(
                base_url=jellyfin_diff_instance.base_url,
                api_key=jellyfin_diff_key,
            )
            code = diff_jellyfin(jellyfin_diff_client, root)
            max_code = max(max_code, code)
        except (ApiClientError, ReconcileError) as e:
            log.error("app_failed", app="jellyfin", error=str(e))
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
