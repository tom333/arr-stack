"""FastAPI application — 11 endpoints + StaticFiles mount placeholder (D-02).

arrconf endpoints:
- GET  /api/config  — read arrconf.yml → RootConfig.model_dump(mode='json')
- PUT  /api/config  — validate body via RootConfig.model_validate → atomic write → diff summary
- GET  /api/schema  — return schemas/arrconf-schema.json content (drives D-13 schema-driven UI)
- POST /api/diff    — stateless preview: accept pending RootConfig, return diff vs on-disk

configarr endpoints (CFGUI-01 / CFGUI-03 / SC#2 / SC#3 / D-09):
- GET  /api/configarr/config  — read configarr.yml → tag-literal dict (SC#2: !env preserved)
- PUT  /api/configarr/config  — validate → atomic write + D-09 anti-leak guard → diff summary
- POST /api/configarr/diff    — stateless preview (SC#4: tag-literal preserving)
- GET  /api/configarr/schema  — return schemas/configarr-schema.json

StaticFiles mount at `/` is enabled if `tools/arrconf-ui/web/dist/` exists.
Plan 15-B builds this directory; until then the mount is skipped (404 on /).

Error contract:
- 404: yml/schema file missing
- 422: pydantic ValidationError → returned with `detail` array (loc/msg/type)
- 500: internal error or D-09 anti-leak guard trip (tag lost after write)
"""

from __future__ import annotations

import json
import logging
from typing import Any

import structlog
from arrconf.config import RootConfig
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from arrconf_ui.configarr_config import ConfigarrRootConfig
from arrconf_ui.configarr_diff import configarr_diff
from arrconf_ui.configarr_diff import has_changes as configarr_has_changes
from arrconf_ui.configarr_io import (
    _tagged_to_literal,
    count_secret_tags,
    merge_preserving_tags,
)
from arrconf_ui.diff import diff_configs, has_changes
from arrconf_ui.io import read_yaml, write_yaml_atomic
from arrconf_ui.locator import (
    arrconf_yml_path,
    configarr_schema_json_path,
    configarr_yml_path,
    repo_root,
    schema_json_path,
    trash_metadata_dir,
)

log = structlog.get_logger()


def _read_current() -> dict[str, Any]:
    """Read arrconf.yml as a plain Python dict (ruyaml CommentedMap → dict via JSON round-trip).

    Why JSON round-trip: pydantic.model_validate handles ruyaml CommentedMap
    via the Mapping protocol BUT ruyaml's tagged scalar types (e.g., dates,
    quoted-empty-string preservation) can leak through model_dump. Going via
    `json.loads(json.dumps(...))` normalizes to plain Python primitives.
    NOT used for the WRITE path — write_yaml_atomic takes the ruyaml object
    directly to preserve comments.
    """
    path = arrconf_yml_path()
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"arrconf.yml not found at {path}",
        )
    raw = read_yaml(path)
    # ruyaml CommentedMap → plain dict (drops comments — fine for read endpoint)
    return json.loads(json.dumps(raw, default=str))  # type: ignore[no-any-return]


def create_app() -> FastAPI:
    """Application factory — kept separate so tests can instantiate fresh apps."""
    app = FastAPI(
        title="arrconf-ui",
        description="Local config editor for charts/arr-stack/files/arrconf.yml",
        version="0.1.0",
    )

    @app.get("/api/config")
    def get_config() -> Any:
        """Return arrconf.yml parsed + validated as JSON (RootConfig.model_dump)."""
        raw = _read_current()
        try:
            validated = RootConfig.model_validate(raw)
        except ValidationError as e:
            # On-disk file is invalid — surface the errors but DON'T 500
            # (operator may have edited the file manually).
            # Normalize ctx values that may contain non-JSON-serializable objects.
            detail = json.loads(json.dumps(e.errors(), default=str))
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": detail, "raw": raw},
            )
        return validated.model_dump(mode="json")

    @app.put("/api/config")
    def put_config(payload: dict[str, Any]) -> Any:
        """Validate payload → atomic write → return semantic diff (D-06 + D-05)."""
        try:
            RootConfig.model_validate(payload)
        except ValidationError as e:
            # e.errors() ctx values may contain non-JSON-serializable objects
            # (e.g., ValueError instances from model_validator). Use json.loads
            # + default=str to normalize before building the JSONResponse.
            detail = json.loads(json.dumps(e.errors(), default=str))
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": detail},
            )
        before = _read_current()
        # Compute diff BEFORE write so the response reflects what was written.
        diff = diff_configs(before, payload)
        # Atomic write: read the current ruyaml CommentedMap to preserve
        # comments, then SHALLOW-MERGE the payload into it so unedited
        # top-level keys (and their comments) are unchanged.
        # NOTE: this is a deliberate first-pass impl. If a future phase needs
        # per-key comment preservation on edited keys, revisit (Phase 15
        # ships with the "comments preserved on unedited keys" baseline).
        target = read_yaml(arrconf_yml_path())
        for top_key in (
            "categories",
            "sonarr",
            "radarr",
            "prowlarr",
            "qbittorrent",
            "seerr",
            "jellyfin",
        ):
            if top_key in payload:
                target[top_key] = payload[top_key]
        write_yaml_atomic(arrconf_yml_path(), target)
        log.info(
            "config_saved",
            has_changes=has_changes(diff),
            changed_sections=[
                k
                for k, v in diff.items()
                if (k == "categories" and (v.get("added") or v.get("modified") or v.get("removed")))
                or (k != "categories" and v.get("changed_fields"))
            ],
        )
        return {"diff": diff, "has_changes": has_changes(diff)}

    @app.post("/api/diff")
    def post_diff(payload: dict[str, Any]) -> Any:
        """Stateless preview: return diff between payload and on-disk arrconf.yml.

        Used by the frontend to power the diff panel BEFORE the operator
        commits the Save action.
        """
        before = _read_current()
        diff = diff_configs(before, payload)
        return {"diff": diff, "has_changes": has_changes(diff)}

    @app.get("/api/schema")
    def get_schema() -> Any:
        """Return the committed JSON Schema (drives D-13 schema-driven UI)."""
        path = schema_json_path()
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schema file not found at {path}",
            )
        return json.loads(path.read_text(encoding="utf-8"))

    # -----------------------------------------------------------------------
    # configarr endpoints — symmetric to the arrconf ones above.
    # SC#3 boundary: NONE of these handlers construct or dial a *arr URL.
    # base_url is stored/echoed verbatim from the file; nothing calls it.
    # -----------------------------------------------------------------------

    @app.get("/api/configarr/config")
    def get_configarr_config() -> Any:
        """Return configarr.yml as tag-literal JSON (SC#2: !env preserved).

        Uses ``_tagged_to_literal`` — NOT ``_read_current`` which JSON-coerces
        and drops ``!env``/``!secret`` tags (Pitfall 1 / RESEARCH line 308).
        """
        path = configarr_yml_path()
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"configarr.yml not found at {path}",
            )
        raw = read_yaml(path)
        literal = _tagged_to_literal(raw)
        try:
            ConfigarrRootConfig.model_validate(literal)
        except ValidationError as e:
            # On-disk file is invalid — surface errors but don't 500
            # (operator may have hand-edited the file).
            detail = json.loads(json.dumps(e.errors(), default=str))
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": detail, "raw": literal},
            )
        # Return the tag-literal dict (NOT model_dump which could coerce types).
        # literal is already a plain Python dict with !env strings preserved.
        return literal

    @app.put("/api/configarr/config")
    def put_configarr_config(payload: dict[str, Any]) -> Any:
        """Validate payload → atomic write → D-09 anti-leak guard → diff (SC#2/D-09).

        D-09: after atomic write, re-reads the file and asserts every
        ``!env``/``!secret`` tag is byte-present. Rolls back + returns 500
        on any tag loss.
        """
        try:
            ConfigarrRootConfig.model_validate(payload)
        except ValidationError as e:
            detail = json.loads(json.dumps(e.errors(), default=str))
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": detail},
            )
        path = configarr_yml_path()
        # Capture pre-write state for diff and D-09 guard
        before_bytes = path.read_bytes()
        before_tree = read_yaml(path)
        expected_tags = count_secret_tags(before_tree)

        # Compute diff on tag-literal snapshot BEFORE write (SC#4)
        before_literal = _tagged_to_literal(before_tree)
        diff = configarr_diff(before_literal, payload)

        # Deep-merge editable leaves into the on-disk ruyaml tree, PRESERVING
        # tagged secret nodes (api_key !env/!secret). Wholesale block replacement
        # demotes TaggedScalars to quoted plain strings whose text still holds
        # "!env" — the leak SC#4 exists to prevent (CR-01).
        target = read_yaml(path)
        merge_preserving_tags(target, payload)
        write_yaml_atomic(path, target)

        # D-09 runtime guard: re-read and assert secret tag NODES survived.
        # Counts actual TaggedScalar nodes, not substrings — a demoted tag keeps
        # its text but is no longer a node, so node-counting catches the loss.
        after_tags = count_secret_tags(read_yaml(path))
        if after_tags < expected_tags:
            path.write_bytes(before_bytes)  # rollback
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="anti-leak guard: !env/!secret tag lost on write",
            )

        log.info(
            "configarr_config_saved",
            has_changes=configarr_has_changes(diff),
        )
        return {"diff": diff, "has_changes": configarr_has_changes(diff)}

    @app.post("/api/configarr/diff")
    def post_configarr_diff(payload: dict[str, Any]) -> Any:
        """Stateless preview: return diff between payload and on-disk configarr.yml.

        MUST NOT write. SC#4: diff runs on tag-literal data.
        """
        path = configarr_yml_path()
        before = _tagged_to_literal(read_yaml(path))
        diff = configarr_diff(before, payload)
        return {"diff": diff, "has_changes": configarr_has_changes(diff)}

    @app.get("/api/configarr/schema")
    def get_configarr_schema() -> Any:
        """Return the committed configarr JSON Schema (readOnly markers for the UI)."""
        path = configarr_schema_json_path()
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schema file not found at {path}",
            )
        return json.loads(path.read_text(encoding="utf-8"))

    # -----------------------------------------------------------------------
    # TRaSH / Recyclarr metadata endpoints (Phase 27 — CFGUI-05, CFGUI-06, CFGUI-08)
    # Serve baked static assets ONLY — NEVER call GitHub or any *arr URL.
    # ADR-5 boundary: no Sonarr/Radarr/Prowlarr URL constructed here.
    # -----------------------------------------------------------------------

    @app.get("/api/trash/custom-formats")
    def get_trash_custom_formats(app: str) -> Any:
        """Return baked TRaSH CF catalog for sonarr or radarr.

        SC#3 boundary: NO *arr URL constructed here. Serves from committed
        static assets only.
        """
        if app not in ("sonarr", "radarr"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="app must be 'sonarr' or 'radarr'",
            )
        path = trash_metadata_dir() / f"{app}-cf.json"
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Catalog not found at {path} — run tools/scripts/fetch-trash-metadata.sh",
            )
        return json.loads(path.read_text(encoding="utf-8"))

    @app.get("/api/trash/quality-profiles")
    def get_trash_quality_profiles(app: str) -> Any:
        """Return baked TRaSH QP catalog for sonarr or radarr.

        SC#3 boundary: NO *arr URL constructed here. Serves from committed
        static assets only.
        """
        if app not in ("sonarr", "radarr"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="app must be 'sonarr' or 'radarr'",
            )
        path = trash_metadata_dir() / f"{app}-qp.json"
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Catalog not found at {path} — run tools/scripts/fetch-trash-metadata.sh",
            )
        return json.loads(path.read_text(encoding="utf-8"))

    @app.get("/api/trash/recyclarr-templates")
    def get_trash_recyclarr_templates(app: str) -> Any:
        """Return baked Recyclarr template list for sonarr or radarr.

        Entries have id + template fields only — no description field.

        SC#3 boundary: NO *arr URL constructed here. Serves from committed
        static assets only.
        """
        if app not in ("sonarr", "radarr"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="app must be 'sonarr' or 'radarr'",
            )
        path = trash_metadata_dir() / f"recyclarr-{app}.json"
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Catalog not found at {path} — run tools/scripts/fetch-trash-metadata.sh",
            )
        return json.loads(path.read_text(encoding="utf-8"))

    # StaticFiles mount (Plan 15-B builds tools/arrconf-ui/web/dist/).
    # Mounted LAST so /api/* routes take precedence.
    dist = repo_root() / "tools" / "arrconf-ui" / "web" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="ui")
    return app


# Module-level instance for ASGI consumers (uvicorn arrconf_ui.app:app)
app = create_app()

# Quiet uvicorn access logs that obscure structlog output during dev.
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
