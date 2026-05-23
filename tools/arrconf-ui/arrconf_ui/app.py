"""FastAPI application — 4 endpoints + StaticFiles mount placeholder (D-02).

Endpoints:
- GET  /api/config  — read arrconf.yml → RootConfig.model_dump(mode='json')
- PUT  /api/config  — validate body via RootConfig.model_validate → atomic write → diff summary
- GET  /api/schema  — return schemas/arrconf-schema.json content (drives D-13 schema-driven UI)
- POST /api/diff    — stateless preview: accept pending RootConfig, return diff vs on-disk

StaticFiles mount at `/` is enabled if `tools/arrconf-ui/web/dist/` exists.
Plan 15-B builds this directory; until then the mount is skipped (404 on /).

Error contract (D-06 validation on Save only):
- 404: arrconf.yml missing
- 422: pydantic ValidationError → returned with `detail` array (loc/msg/type)
- 500: anything else
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

from arrconf_ui.diff import diff_configs, has_changes
from arrconf_ui.io import read_yaml, write_yaml_atomic
from arrconf_ui.locator import arrconf_yml_path, repo_root, schema_json_path

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
