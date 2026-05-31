"""arrconf CLI entrypoint — 4 subcommands per D-01..D-04 + REQ-cli-subcommands.

Exit code contract (CLAUDE.md CLI section):
    0 — success
    1 — application failure (e.g. upstream API error)
    2 — config error (parse / validation / missing API key)
    3 — drift detected by ``diff`` (only emitted by ``diff``)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
import typer

from arrconf.audit import run_audit, verify_audit
from arrconf.client_base import JellyfinClient, ProwlarrClient, RadarrClient, SonarrClient
from arrconf.config import RootConfig, load_config
from arrconf.diff_cmd import diff_jellyfin, diff_prowlarr, diff_radarr, diff_sonarr
from arrconf.dump import dump_jellyfin, dump_sonarr
from arrconf.exceptions import (
    ApiClientError,
    ConfigError,
    ReconcileError,
    ScopeViolationError,
)
from arrconf.generators.categories import (
    generate_anime_tag_labels,
    generate_jellyfin_libraries,
    generate_qbit_categories,
    generate_radarr_resources,
    generate_sonarr_resources,
)
from arrconf.generators.intent import generate_cross_seed
from arrconf.intent_config import IntentConfig, load_intent
from arrconf.logging import configure_logging
from arrconf.reconcilers.prowlarr import reconcile_prowlarr
from arrconf.reconcilers.radarr import reconcile_radarr
from arrconf.reconcilers.sonarr import reconcile_sonarr
from arrconf.schema_gen import write_intent_schema, write_schema
from arrconf.settings import Settings


def _resolve_seerr_anime_tag_ids(
    root: RootConfig,
    sonarr_client: SonarrClient,
    log: structlog.BoundLogger,
) -> list[int]:
    """Seerr animeTags resolution chain (Plan 10-F, RESEARCH.md Pattern 5).

    Returns Sonarr integer tag IDs for every cfg.categories entry where
    kind=='series' AND profile=='anime'. Returns [] if no anime series
    categories exist or if the tags haven't been created in Sonarr yet
    (caller passes the resolved IDs directly to reconcile_seerr).

    Issues ONE extra GET to Sonarr /tag — cheap, idempotent.

    kind=='series' filter is applied HERE (not in generate_anime_tag_labels)
    because Seerr.sonarr_service.animeTags is Sonarr-side routing only;
    Radarr has no animeTags field (RESEARCH §Pattern 5, Pitfall 3).
    """
    # generate_anime_tag_labels returns ALL anime-profile labels (series + movies).
    # Filter to kind=="series" — Seerr.animeTags is Sonarr-side only; Radarr-side
    # has no animeTags field (RESEARCH §Pattern 5, Pitfall 3).
    all_anime_labels = set(generate_anime_tag_labels(root))
    series_anime_labels = [
        c.name
        for c in root.categories
        if c.profile == "anime" and c.kind == "series" and c.name in all_anime_labels
    ]
    if not series_anime_labels:
        return []

    raw_tags: list[dict[str, Any]] = sonarr_client.get("/tag")
    resolved: list[int] = []
    missing: list[str] = []
    for label in series_anime_labels:
        match = next((t for t in raw_tags if t.get("label") == label), None)
        if match is None or match.get("id") is None:
            missing.append(label)
            continue
        resolved.append(int(match["id"]))

    if missing:
        log.warning(
            "seerr_animetags_label_unresolved",
            labels=missing,
            hint=(
                "Anime-profile category labels not yet present in Sonarr's tag list. "
                "They will be created on this reconcile run; rerun arrconf apply to "
                "populate Seerr.animeTags with the new IDs (D-02 transition step)."
            ),
        )

    return resolved


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


def _qbit_creds_required_for_sonarr_radarr(root: RootConfig, targets: set[str]) -> bool:
    """Return True if a Sonarr or Radarr reconcile/diff will need QBT_USER/QBT_PASS.

    Phase 18 (REQ-qbit-post-credentials): the Categories generator emits qBit
    download_clients with empty ``username``/``password`` fields[]; the helper
    ``_resolve_qbit_credentials_from_env`` substitutes them from env at reconcile
    time, raising ``ConfigError`` when env is also unset. To convert that
    in-reconcile failure into a pre-flight fail-fast (so Steps 1-5 don't write
    to the cluster), this predicate is evaluated BEFORE any Sonarr/Radarr client
    is constructed.

    True when:
      - At least one of {sonarr, radarr} is in ``targets`` AND
      - That app's ``main`` instance is declared in YAML AND
      - ``root.categories`` is non-empty (the generator emits at least one
        qBit DC with empty creds — the production shape since v0.3.0).

    A non-empty ``categories`` list is the dispositive signal because
    ``generate_sonarr_resources`` / ``generate_radarr_resources`` always emit a
    qBit DC per category, and those DCs always carry ``username=""`` /
    ``password=""`` from the generator (the Phase 18 helper is the only path
    that fills them in).
    """
    if not root.categories:
        return False
    if "sonarr" in targets and "main" in root.sonarr:
        return True
    if "radarr" in targets and "main" in root.radarr:
        return True
    return False


@app.callback()
def main(
    ctx: typer.Context,
    config: Path = typer.Option(
        Path("/etc/arrconf/arrconf.yml"),
        "--config",
        "-c",
        help="Path to arrconf YAML config",
    ),
    intent: Path = typer.Option(
        Path("/etc/arrconf/intent.yml"),
        "--intent",
        "-i",
        help="Path to intent.yml (sagas, tools). Optional — skipped if absent.",
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
    ctx.obj = {"config_path": config, "intent_path": intent}


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

    # Phase 29 (SAGAS-01 / D-01): optional intent.yml load.
    # Guard: absent intent.yml = no crash, intent_cfg stays None (backward-compatible
    # with clusters that have no intent.yml — T-29-01 availability mitigation).
    intent_path: Path = ctx.obj["intent_path"]
    intent_cfg: IntentConfig | None = None
    if intent_path.exists():
        try:
            intent_cfg = load_intent(intent_path)
        except ConfigError as e:
            log.error("intent_config_error", error=str(e))
            raise typer.Exit(code=2) from e

    targets = _selected_apps(apps)
    settings = Settings()
    failures: list[str] = []

    # Phase 18 (REQ-qbit-post-credentials): pre-flight QBT_USER/QBT_PASS gate
    # for Sonarr/Radarr. Mirrors the qBittorrent gate (lines 269-281) so the
    # helper's ConfigError never fires inside reconcile() — Steps 1-5 (tags,
    # indexers, root_folders, RPMs) must not be POSTed before the credential
    # contract is validated. Fixes CR-02 (partial cluster writes) and CR-01
    # (uncaught ConfigError → traceback exit 1 instead of exit 2).
    if _qbit_creds_required_for_sonarr_radarr(root, targets):
        missing = [
            k
            for k, v in (("QBT_USER", settings.qbt_user), ("QBT_PASS", settings.qbt_pass))
            if not v
        ]
        if missing:
            log.error(
                "missing_env_vars",
                apps=sorted(targets & {"sonarr", "radarr"}),
                missing=missing,
            )
            raise typer.Exit(code=2)

    if "sonarr" in targets and "main" in root.sonarr:
        instance = root.sonarr["main"]
        # Phase 12-A (D-03/D-04): generators called here; derived object passed directly
        # to reconcile_sonarr — merge_with_manual removed (Plan A, v0.4.0 cleanup).
        sonarr_derived = generate_sonarr_resources(root)
        # Fast-fail when SONARR_API_KEY missing — no silent fallback to "" (CLAUDE.md
        # "no silent failures"). Symptom of the old fallback: 401 from upstream with
        # no clear hint that env was missing.
        if not settings.sonarr_api_key:
            log.error("missing_api_key", app="sonarr", env_var="SONARR_API_KEY")
            raise typer.Exit(code=2)
        api_key = settings.sonarr_api_key.get_secret_value()
        try:
            client = SonarrClient(base_url=instance.base_url, api_key=api_key)
            result = reconcile_sonarr(
                client, instance, sonarr_derived, dry_run=dry_run or settings.arrconf_dry_run
            )
            if all(
                a == "no-op" or a.startswith("prune-")
                for a in (p.action.value for p in result.plan)
            ):
                log.info("no-op", app="sonarr", count=len(result.plan))
            else:
                log.info("apply_complete", app="sonarr", actions=result.actions_taken)
        except ConfigError as e:
            # Phase 18 (CR-01 defense-in-depth): the helper raises ConfigError
            # when YAML+env credentials are both empty. The pre-flight gate
            # above is the primary path; this handler catches stragglers (e.g.
            # tests that exercise reconcile_sonarr directly bypassing the gate)
            # so they still exit with the documented code 2 instead of a
            # traceback (exit 1).
            log.error("config_error", app="sonarr", error=str(e))
            raise typer.Exit(code=2) from e
        except (ApiClientError, ReconcileError) as e:
            log.error("app_failed", app="sonarr", error=str(e))
            failures.append("sonarr")

    # NEW: Radarr branch (Plan 06 wiring — D-03-01 full parity).
    if "radarr" in targets and "main" in root.radarr:
        radarr_instance = root.radarr["main"]
        # Phase 12-A (D-03/D-04): generators called here; derived object passed directly
        # to reconcile_radarr — merge_with_manual removed (Plan A, v0.4.0 cleanup).
        radarr_derived = generate_radarr_resources(root)
        if not settings.radarr_api_key:
            log.error("missing_api_key", app="radarr", env_var="RADARR_API_KEY")
            raise typer.Exit(code=2)
        radarr_api_key = settings.radarr_api_key.get_secret_value()
        try:
            radarr_client = RadarrClient(base_url=radarr_instance.base_url, api_key=radarr_api_key)
            radarr_result = reconcile_radarr(
                radarr_client,
                radarr_instance,
                radarr_derived,
                dry_run=dry_run or settings.arrconf_dry_run,
            )
            if all(
                a == "no-op" or a.startswith("prune-")
                for a in (p.action.value for p in radarr_result.plan)
            ):
                log.info("no-op", app="radarr", count=len(radarr_result.plan))
            else:
                log.info("apply_complete", app="radarr", actions=radarr_result.actions_taken)
        except ConfigError as e:
            # Phase 18 (CR-01 defense-in-depth): mirror of Sonarr branch.
            log.error("config_error", app="radarr", error=str(e))
            raise typer.Exit(code=2) from e
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
            # Phase 12-A (D-03/D-04): generator called here; list passed directly
            # to reconcile_qbittorrent — merge_with_manual removed (Plan A, v0.4.0 cleanup).
            qbit_generated = generate_qbit_categories(root)
            assert settings.qbt_user is not None and settings.qbt_pass is not None
            qbit_client = QbittorrentClient(
                base_url=qbit_instance.base_url,
                username=settings.qbt_user.get_secret_value(),
                password=settings.qbt_pass.get_secret_value(),
            )
            qbit_result = reconcile_qbittorrent(
                qbit_client,
                qbit_instance,
                qbit_generated,
                dry_run=dry_run or settings.arrconf_dry_run,
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

            # Phase 12-A (D-03/D-04): animeTags resolved here and passed directly to
            # reconcile_seerr — merge_with_manual removed (Plan A, v0.4.0 cleanup).
            # Requires Sonarr to have reconciled first so the freshly-created tags are
            # GET-able via /api/v3/tag. Sonarr client reconstructed here for the second GET.
            # Skip resolution if Sonarr wasn't in scope (operator --apps seerr without
            # sonarr) or SONARR_API_KEY is missing — resolved_anime_ids = [] (no override).
            if "sonarr" in targets and "main" in root.sonarr and settings.sonarr_api_key:
                sonarr_for_resolution = SonarrClient(
                    base_url=root.sonarr["main"].base_url,
                    api_key=settings.sonarr_api_key.get_secret_value(),
                )
                resolved_anime_ids = _resolve_seerr_anime_tag_ids(root, sonarr_for_resolution, log)
            else:
                resolved_anime_ids = []
                log.info(
                    "seerr_animetags_resolution_skipped",
                    reason="sonarr not in --apps scope or missing SONARR_API_KEY",
                )

            seerr_api_key = settings.seerr_api_key.get_secret_value()
            seerr_client = SeerrClient(
                base_url=seerr_instance.base_url,
                api_key=seerr_api_key,
            )
            seerr_result = reconcile_seerr(
                seerr_client,
                seerr_instance,
                resolved_anime_ids,
                dry_run=dry_run or settings.arrconf_dry_run,
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
            # Phase 12-A (D-03/D-04): generator called here; list passed directly
            # to reconcile_jellyfin — merge_with_manual removed (Plan A, v0.4.0 cleanup).
            jellyfin_generated = generate_jellyfin_libraries(root)
            jellyfin_api_key = settings.jellyfin_api_key.get_secret_value()
            jellyfin_client = JellyfinClient(
                base_url=jellyfin_instance.base_url,
                api_key=jellyfin_api_key,
            )
            jellyfin_result = reconcile_jellyfin(
                jellyfin_client,
                jellyfin_instance,
                jellyfin_generated,
                dry_run=dry_run or settings.arrconf_dry_run,
            )
            if not jellyfin_result.actions_taken:
                log.info("no-op", app="jellyfin")
            else:
                log.info("apply_complete", app="jellyfin", actions=jellyfin_result.actions_taken)
        except (ApiClientError, ReconcileError) as e:
            log.error("app_failed", app="jellyfin", error=str(e))
            failures.append("jellyfin")

    # Phase 29 (SAGAS-02 / D-07): Saga reconcile branches run AFTER all existing app
    # branches (quality profiles must exist before collection reconcile reads them).
    if intent_cfg is not None and intent_cfg.sagas:
        # SAGAS-02: Radarr Collections reconcile (kind=movies only)
        if "radarr" in targets and "main" in root.radarr and settings.radarr_api_key:
            try:
                from arrconf.reconcilers.radarr import (  # noqa: PLC0415
                    reconcile_radarr_collections,
                )

                radarr_saga_client = RadarrClient(
                    base_url=root.radarr["main"].base_url,
                    api_key=settings.radarr_api_key.get_secret_value(),
                )
                saga_actions = reconcile_radarr_collections(
                    radarr_saga_client,
                    intent_cfg.sagas,
                    dry_run=dry_run or settings.arrconf_dry_run,
                )
                log.info("apply_complete", app="radarr_collections", actions=saga_actions)
            except ConfigError as e:
                log.error("config_error", app="radarr_collections", error=str(e))
                raise typer.Exit(code=2) from e
            except (ApiClientError, ReconcileError) as e:
                log.error("app_failed", app="radarr_collections", error=str(e))
                failures.append("radarr_collections")

        # SAGAS-04: Jellyfin series BoxSets — best-effort (ADR-9, D-07)
        if "jellyfin" in targets and "main" in root.jellyfin and settings.jellyfin_api_key:
            try:
                from arrconf.reconcilers.jellyfin import (  # noqa: PLC0415
                    _reconcile_sagas_boxsets,
                )

                jellyfin_saga_client = JellyfinClient(
                    base_url=root.jellyfin["main"].base_url,
                    api_key=settings.jellyfin_api_key.get_secret_value(),
                )
                series_sagas = [s for s in intent_cfg.sagas if s.kind == "series"]
                saga_box_actions = _reconcile_sagas_boxsets(
                    jellyfin_saga_client,
                    series_sagas,
                    dry_run=dry_run or settings.arrconf_dry_run,
                )
                log.info("apply_complete", app="jellyfin_sagas", actions=saga_box_actions)
            except (ApiClientError, ReconcileError) as e:
                log.error("app_failed", app="jellyfin_sagas", error=str(e))
                failures.append("jellyfin_sagas")

        # SAGAS-04 (Sonarr tagging sub-step): tag member series arrconf-managed in Sonarr.
        # Runs AFTER BoxSet creation so the BoxSet is the primary deliverable.
        # _ensure_managed_tag ONLY creates/gets the tag record — must ALSO PUT /series/editor
        # to actually apply the tag (mirrors _reconcile_series_tags — R-02 applyTags="add"
        # so operator-assigned tags are never removed).
        if "sonarr" in targets and "main" in root.sonarr and settings.sonarr_api_key:
            try:
                from arrconf.reconcilers.sonarr import (  # noqa: PLC0415
                    SERIES_EDITOR_PATH,
                    _ensure_managed_tag,
                )

                sonarr_saga_client = SonarrClient(
                    base_url=root.sonarr["main"].base_url,
                    api_key=settings.sonarr_api_key.get_secret_value(),
                )
                _dry = dry_run or settings.arrconf_dry_run

                # Step 1: ensure the arrconf-managed tag exists (create if absent)
                managed_tag = _ensure_managed_tag(sonarr_saga_client, dry_run=_dry)

                # Step 2: collect all member titles from kind=series sagas
                series_titles: set[str] = {
                    title
                    for s in intent_cfg.sagas
                    if s.kind == "series"
                    for title in (s.items or [])
                }

                if series_titles:
                    # Step 3: GET /series, resolve titles → Sonarr series ids
                    raw_series = sonarr_saga_client.get("/series")
                    series_ids = [
                        s["id"]
                        for s in raw_series
                        if s.get("title") in series_titles and s.get("id") is not None
                    ]
                    unmatched = series_titles - {
                        s.get("title") for s in raw_series if s.get("title") in series_titles
                    }
                    for title in unmatched:
                        log.warning(
                            "sonarr_saga_series_unresolved",
                            title=title,
                            hint="Check that the title in intent.yml matches Sonarr exactly",
                        )

                    # Step 4: apply tag via PUT /series/editor with applyTags="add"
                    # (applyTags="add" preserves operator-assigned tags — R-02)
                    if series_ids and not _dry:
                        sonarr_saga_client._request(
                            "PUT",
                            SERIES_EDITOR_PATH,
                            json={
                                "seriesIds": series_ids,
                                "tags": [managed_tag.id],
                                "applyTags": "add",
                                "moveFiles": False,
                            },
                        )
                        log.info(
                            "sonarr_saga_tags_applied",
                            count=len(series_ids),
                            tag_id=managed_tag.id,
                        )
                    elif series_ids and _dry:
                        log.info(
                            "dry_run_skip",
                            resource="sonarr_saga_tags",
                            count=len(series_ids),
                        )

                log.info("apply_complete", app="sonarr_saga_tags")
            except (ApiClientError, ReconcileError) as e:
                # Tagging is secondary (BoxSet is primary); best-effort: log + continue
                log.warning("app_failed", app="sonarr_saga_tags", error=str(e))
                failures.append("jellyfin_sagas")

    if failures:
        raise typer.Exit(code=1)
    raise typer.Exit(code=0)


@app.command()
def audit(
    ctx: typer.Context,
    apps: str | None = typer.Option(None, help="Comma-separated apps (default: all 5)"),
    output: Path = typer.Option(
        Path(".planning/phases/20-categories-cleanup-audit/20-AUDIT.md"),
        "--output",
        "-o",
        help="Path for the generated audit markdown",
    ),
) -> None:
    """Read-only inventory of v0.2.0 legacy state across the stack (Phase 20)."""
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

    # Per-app env-var fail-fast gates — mirrors apply (lines 245-247, 280-282, etc.)
    required_keys: list[tuple[str, str, Any]] = []
    if "sonarr" in targets and "main" in root.sonarr:
        required_keys.append(("sonarr", "SONARR_API_KEY", settings.sonarr_api_key))
    if "radarr" in targets and "main" in root.radarr:
        required_keys.append(("radarr", "RADARR_API_KEY", settings.radarr_api_key))
    if "seerr" in targets and "main" in root.seerr:
        required_keys.append(("seerr", "SEERR_API_KEY", settings.seerr_api_key))
    if "jellyfin" in targets and "main" in root.jellyfin:
        required_keys.append(("jellyfin", "JELLYFIN_API_KEY", settings.jellyfin_api_key))
    for app_name, env_var, val in required_keys:
        if not val:
            log.error("missing_api_key", app=app_name, env_var=env_var)
            raise typer.Exit(code=2)
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
        run_audit(root, settings, output_path=output, targets=targets)
    except ConfigError as e:
        log.error("config_error", error=str(e))
        raise typer.Exit(code=2) from e
    log.info("audit_complete", output=str(output))
    raise typer.Exit(code=0)


@app.command(name="audit-verify")
def audit_verify_cmd(
    ctx: typer.Context,
    input: Path = typer.Option(
        Path(".planning/phases/20-categories-cleanup-audit/20-AUDIT.md"),
        "--input",
        "-i",
        help="Path of the 20-AUDIT.md to verify",
    ),
) -> None:
    """Verify 20-AUDIT.md pre-commit gates: no `?` cells, YAML parses, paths/tags exist."""
    log = structlog.get_logger()
    try:
        root = load_config(ctx.obj["config_path"])
    except ConfigError as e:
        log.error("config_error", error=str(e))
        raise typer.Exit(code=2) from e

    settings = Settings()
    # For Gate 4 (live tag re-GET) we need Sonarr+Radarr clients if available.
    # If their API keys are missing, fall back to skipping Gate 4 (log a warning).
    sonarr_client: SonarrClient | None = None
    radarr_client: RadarrClient | None = None
    if "main" in root.sonarr and settings.sonarr_api_key:
        sonarr_client = SonarrClient(
            base_url=root.sonarr["main"].base_url,
            api_key=settings.sonarr_api_key.get_secret_value(),
        )
    if "main" in root.radarr and settings.radarr_api_key:
        radarr_client = RadarrClient(
            base_url=root.radarr["main"].base_url,
            api_key=settings.radarr_api_key.get_secret_value(),
        )
    if sonarr_client is None or radarr_client is None:
        log.warning(
            "audit_verify_tag_gate_skipped",
            reason="missing API keys — Gate 4 live tag re-GET skipped",
        )

    exit_code = verify_audit(input, root, sonarr_client, radarr_client)
    raise typer.Exit(code=exit_code)


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

    # Phase 18 (REQ-qbit-post-credentials): pre-flight QBT_USER/QBT_PASS gate
    # for Sonarr/Radarr diff. diff_sonarr/diff_radarr exercises the same
    # helper chain as reconcile_sonarr/reconcile_radarr — pre-validating the
    # env contract here keeps the diff CLI in line with apply's fail-fast
    # semantics (exit 2 instead of an in-reconcile ConfigError traceback).
    if _qbit_creds_required_for_sonarr_radarr(root, targets):
        missing = [
            k
            for k, v in (("QBT_USER", settings.qbt_user), ("QBT_PASS", settings.qbt_pass))
            if not v
        ]
        if missing:
            log.error(
                "missing_env_vars",
                apps=sorted(targets & {"sonarr", "radarr"}),
                missing=missing,
            )
            raise typer.Exit(code=2)

    if "sonarr" in targets and "main" in root.sonarr:
        instance = root.sonarr["main"]
        # Phase 12-B: Plan-A shim removed — .items attribute deleted from Section models (D-01).
        # diff_sonarr calls the generator and passes derived as 3rd arg (Plan A, Phase 12-A).
        # Fast-fail when SONARR_API_KEY missing — mirrors apply/dump branches.
        if not settings.sonarr_api_key:
            log.error("missing_api_key", app="sonarr", env_var="SONARR_API_KEY")
            raise typer.Exit(code=2)
        api_key = settings.sonarr_api_key.get_secret_value()
        try:
            client = SonarrClient(base_url=instance.base_url, api_key=api_key)
            code = diff_sonarr(client, root)
            max_code = max(max_code, code)
        except ConfigError as e:
            # Phase 18 (CR-01 defense-in-depth): same straggler catch as apply.
            log.error("config_error", app="sonarr", error=str(e))
            raise typer.Exit(code=2) from e
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
        # Phase 12-B: Plan-A shim removed — .items attribute deleted from Section models (D-01).
        # diff_radarr calls the generator and passes derived as 3rd arg (Plan A, Phase 12-A).
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
        except ConfigError as e:
            # Phase 18 (CR-01 defense-in-depth): mirror of Sonarr diff branch.
            log.error("config_error", app="radarr", error=str(e))
            raise typer.Exit(code=2) from e
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
            # Phase 12-B (D-01): items attribute deleted; diff_qbittorrent calls the
            # generator inline (Plan A, Phase 12-A pattern).
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

    # Phase 6: Seerr diff branch (Pitfall 5 — diff must use same merged shape as apply).
    # animeTags resolution runs here so that `diff` produces the same Seerr desired-state
    # as `apply`. The actual diff_seerr function is deferred to a future plan (Phase 10-J
    # sweep or equivalent) — this branch performs the pre-merge only.
    if "seerr" in targets and "main" in root.seerr:
        if not settings.seerr_api_key:
            log.error("missing_api_key", app="seerr", env_var="SEERR_API_KEY")
            raise typer.Exit(code=2)
        # Phase 12-B: animeTags shim removed from diff branch — diff_seerr does not
        # exist yet (deferred). animeTags YAML field deleted; pydantic field survives
        # on SeerrSonarrServiceSection for reconcile_seerr's runtime population.
        # diff_seerr is not yet wired (deferred to Phase 10-J sweep plan).
        log.info(
            "diff_not_implemented",
            app="seerr",
            hint="Seerr diff is deferred to Phase 10-J",
        )

    # Phase 7: Jellyfin diff branch (D-07-INSTANCE-01, SC#4 dispositive).
    if "jellyfin" in targets and "main" in root.jellyfin:
        jellyfin_diff_instance = root.jellyfin["main"]
        # Phase 12-B (D-01): items attribute deleted; diff_jellyfin calls the
        # generator inline (Plan A, Phase 12-A pattern).
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


@app.command(name="intent-schema-gen")
def intent_schema_gen_cmd(
    output: Path = typer.Option(
        Path("schemas/intent-schema.json"),
        "--output",
        "-o",
        help="Output JSON Schema path (INTENT-01)",
    ),
) -> None:
    """Export JSON Schema (Draft 2020-12) from IntentConfig (INTENT-01)."""
    log = structlog.get_logger()
    output.parent.mkdir(parents=True, exist_ok=True)
    write_intent_schema(output)
    log.info("intent_schema_written", path=str(output))
    raise typer.Exit(code=0)


@app.command()
def generate(
    intent: Path = typer.Option(
        Path("charts/arr-stack/files/intent.yml"),
        "--intent",
        "-i",
        help="Path to intent.yml (hand-edited source of truth).",
    ),
    output_dir: Path = typer.Option(
        Path("charts/arr-stack/files/"),
        "--output-dir",
        "-o",
        help="Directory for generated output files (co-located with arrconf.yml).",
    ),
    check: bool = typer.Option(
        False,
        "--check",
        help="Verify committed files match intent; exit 1 on drift (CI mode).",
    ),
) -> None:
    """Generate committed configs from intent.yml.

    Use --check in CI (INTENT-02/INTENT-03, D-06/D-07).
    """
    log = structlog.get_logger()
    try:
        intent_cfg = load_intent(intent)
    except ConfigError as e:
        log.error("intent_config_error", error=str(e))
        raise typer.Exit(code=2) from e

    drift = False
    if intent_cfg.tools.cross_seed is not None:
        rendered = generate_cross_seed(intent_cfg.tools.cross_seed)
        target = output_dir / "cross-seed" / "config.js"
        if check:
            if not target.exists() or target.read_text(encoding="utf-8") != rendered:
                log.error("generate_drift", file=str(target))
                drift = True
            else:
                log.info("generate_ok", file=str(target))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(rendered, encoding="utf-8")
            log.info("generate_written", file=str(target))

    raise typer.Exit(code=1 if drift else 0)


if __name__ == "__main__":
    app()
