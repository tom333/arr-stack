"""FastAPI application — intent endpoints + read-only inspectors (D-02, D-34-04).

intent endpoints (UI-01 / UI-04 backend):
- GET  /api/intent         — read intent.yml → IntentConfig.model_dump(mode='json')
- GET  /api/intent/schema  — return schemas/intent-schema.json (drives schema-driven UI)
- POST /api/intent/diff    — stateless preview: generate arrconf.yml + configarr.yml from
                             payload, diff vs on-disk, return two unified text diffs
- PUT  /api/intent         — validate → write intent.yml → regenerate arrconf.yml + configarr.yml

arrconf read-only inspector (GET kept; PUT removed — D-34-04):
- GET  /api/config  — read arrconf.yml → RootConfig.model_dump(mode='json')
- GET  /api/schema  — return schemas/arrconf-schema.json
- POST /api/diff    — stateless preview vs on-disk arrconf.yml

configarr read-only inspector (GET kept; PUT removed — D-34-04):
- GET  /api/configarr/config  — read configarr.yml → tag-literal dict (SC#2: !env preserved)
- POST /api/configarr/diff    — stateless preview (SC#4: tag-literal preserving)
- GET  /api/configarr/schema  — return schemas/configarr-schema.json

TRaSH / Recyclarr metadata (read-only static assets):
- GET  /api/trash/custom-formats, /api/trash/quality-profiles, /api/trash/recyclarr-templates

StaticFiles mount at `/` is enabled if `tools/arrconf-ui/web/dist/` exists.

Error contract:
- 404: yml/schema file missing
- 422: pydantic ValidationError → returned with `detail` array (loc/msg/type)
- 500: internal error or D-09 anti-leak guard trip (tag lost after write)
"""

from __future__ import annotations

import difflib
import io as _io
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import structlog
from arrconf.config import RootConfig
from arrconf.exceptions import ConfigError
from arrconf.generators.configarr import generate_configarr_yml
from arrconf.generators.intent import generate_arrconf_yml
from arrconf.intent_config import IntentConfig, load_intent
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from ruyaml import YAML

from arrconf_ui.configarr_config import ConfigarrRootConfig
from arrconf_ui.configarr_diff import configarr_diff
from arrconf_ui.configarr_diff import has_changes as configarr_has_changes
from arrconf_ui.configarr_io import _tagged_to_literal
from arrconf_ui.diff import diff_configs, has_changes
from arrconf_ui.io import read_yaml
from arrconf_ui.locator import (
    arrconf_yml_path,
    configarr_schema_json_path,
    configarr_yml_path,
    intent_schema_json_path,
    intent_yml_path,
    repo_root,
    schema_json_path,
    trash_metadata_dir,
)

log = structlog.get_logger()

# Header prepended to intent.yml on every UI save (Pitfall 2, option 1).
# Keeps the $schema modeline so VS Code YAML server retains autocomplete.
_INTENT_HEADER = (
    "# yaml-language-server: $schema=../../../schemas/intent-schema.json\n"
    "# HAND-EDITED — source of truth for 'arrconf generate'\n"
)


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


def _write_text_atomic(path: Path, text: str) -> None:
    """Atomically write a text string to path using tempfile + os.replace.

    Same crash-safety recipe as write_yaml_atomic but for pre-serialized text
    (plain str, not ruyaml CommentedMap). Used for intent.yml which is written
    from a JSON payload (YAML safe dump) and for generated arrconf/configarr files.
    """
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    try:
        tmp.write(text)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, path)
    except Exception:
        tmp.close()
        try:
            os.unlink(tmp.name)
        except FileNotFoundError:
            pass
        raise


def create_app() -> FastAPI:
    """Application factory — kept separate so tests can instantiate fresh apps."""
    app = FastAPI(
        title="arrconf-ui",
        description="Local config editor — intent.yml is the only editable source (D-34-04)",
        version="0.1.0",
    )

    # -----------------------------------------------------------------------
    # Intent endpoints (UI-01 / UI-04 backend)
    # SC#3 boundary: NONE of these handlers construct or dial a *arr URL.
    # base_url is stored/echoed verbatim; nothing calls it.
    # -----------------------------------------------------------------------

    @app.get("/api/intent")
    def get_intent() -> Any:
        """Return intent.yml parsed + validated as JSON (IntentConfig.model_dump)."""
        path = intent_yml_path()
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"intent.yml not found at {path}",
            )
        try:
            cfg = load_intent(path)
        except ConfigError as e:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": str(e)},
            )
        return cfg.model_dump(mode="json")

    @app.get("/api/intent/schema")
    def get_intent_schema() -> Any:
        """Return the committed intent JSON Schema (drives schema-driven UI)."""
        path = intent_schema_json_path()
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Intent schema file not found at {path}",
            )
        return json.loads(path.read_text(encoding="utf-8"))

    @app.post("/api/intent/diff")
    def post_intent_diff(payload: dict[str, Any]) -> Any:
        """Stateless preview: generate + diff intent against on-disk files.

        Generates arrconf.yml + configarr.yml from payload and diffs against
        the on-disk versions, returning two unified text diffs.

        SC#3 boundary: this handler never constructs or dials a *arr URL.
        Generation is pure (no I/O beyond reading on-disk files for diff).
        """
        try:
            intent_cfg = IntentConfig.model_validate(payload)
        except ValidationError as e:
            detail = json.loads(json.dumps(e.errors(), default=str))
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": detail},
            )

        new_arrconf = generate_arrconf_yml(intent_cfg)
        new_configarr = generate_configarr_yml(intent_cfg)

        current_arrconf = (
            arrconf_yml_path().read_text("utf-8") if arrconf_yml_path().exists() else ""
        )
        current_configarr = (
            configarr_yml_path().read_text("utf-8") if configarr_yml_path().exists() else ""
        )

        arrconf_diff_str = "\n".join(
            difflib.unified_diff(
                current_arrconf.splitlines(),
                new_arrconf.splitlines(),
                fromfile="arrconf.yml (actuel)",
                tofile="arrconf.yml (généré)",
                lineterm="",
            )
        )
        configarr_diff_str = "\n".join(
            difflib.unified_diff(
                current_configarr.splitlines(),
                new_configarr.splitlines(),
                fromfile="configarr.yml (actuel)",
                tofile="configarr.yml (généré)",
                lineterm="",
            )
        )
        return {
            "arrconf_diff": arrconf_diff_str,
            "configarr_diff": configarr_diff_str,
            "has_changes": bool(arrconf_diff_str or configarr_diff_str),
        }

    @app.put("/api/intent")
    def put_intent(payload: dict[str, Any]) -> Any:
        """Validate → write intent.yml → regenerate arrconf.yml + configarr.yml (D-34-06).

        SC#3 boundary: this handler never constructs or dials a *arr URL.
        Calls only pure generate_* functions + file writes.

        Write order (D-34-06): intent.yml first (source of truth), then both
        generated files. On validation failure, no files are written.
        """
        try:
            intent_cfg = IntentConfig.model_validate(payload)
        except ValidationError as e:
            detail = json.loads(json.dumps(e.errors(), default=str))
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": detail},
            )

        # Serialize intent.yml using YAML(typ="safe") — intent payload is a plain
        # dict from JSON, not a ruyaml CommentedMap. Pitfall 1: do NOT use
        # write_yaml_atomic (rt-mode) for plain dicts — safe mode gives canonical
        # block-style output.
        yaml = YAML(typ="safe")
        yaml.default_flow_style = False
        yaml.indent(mapping=2, sequence=4, offset=2)
        buf = _io.StringIO()
        yaml.dump(payload, buf)

        # Prepend $schema modeline (Pitfall 2, option 1) so VS Code YAML server
        # retains autocomplete after a UI save.
        intent_text = _INTENT_HEADER + buf.getvalue()
        _write_text_atomic(intent_yml_path(), intent_text)

        # Write generated files VERBATIM from generator return strings (Pitfall 4:
        # do NOT re-dump; generators already prepend their own headers).
        arrconf_yml_path().write_text(generate_arrconf_yml(intent_cfg), encoding="utf-8")
        configarr_yml_path().write_text(generate_configarr_yml(intent_cfg), encoding="utf-8")

        log.info("intent_saved")
        return {"saved": True}

    # -----------------------------------------------------------------------
    # arrconf read-only inspector (PUT removed — D-34-04).
    # SC#3 boundary: NONE of these handlers construct or dial a *arr URL.
    # -----------------------------------------------------------------------

    @app.get("/api/config")
    def get_config() -> Any:
        """Return arrconf.yml parsed + validated as JSON (RootConfig.model_dump).

        Read-only inspector — PUT /api/config was removed in D-34-04.
        arrconf.yml is now 100% generated; intent.yml is the only editable source.
        """
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
    # configarr read-only inspector (PUT removed — D-34-04).
    # SC#3 boundary: NONE of these handlers construct or dial a *arr URL.
    # base_url is stored/echoed verbatim from the file; nothing calls it.
    # -----------------------------------------------------------------------

    @app.get("/api/configarr/config")
    def get_configarr_config() -> Any:
        """Return configarr.yml as tag-literal JSON (SC#2: !env preserved).

        Uses ``_tagged_to_literal`` — NOT ``_read_current`` which JSON-coerces
        and drops ``!env``/``!secret`` tags (Pitfall 1 / RESEARCH line 308).

        Read-only inspector — PUT /api/configarr/config was removed in D-34-04.
        configarr.yml is now 100% generated; intent.yml is the only editable source.
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
