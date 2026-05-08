"""Dump current cluster state to YAML.

Emits the yaml-language-server modeline as line 1 of the output (D-16).
For Phase 1 the modeline path is hardcoded for the ``examples/<file>.yml``
case (the only target of ROADMAP success criteria 3-4).

TODO Phase 4: replace with ``os.path.relpath(SCHEMA_FILE_ABS_PATH, output_path.parent)``
resolved from the package install root. Phase 1 hardcodes the
``examples/<file>.yml`` heuristic because it is the only target of
ROADMAP success criteria 3-4. The Phase 4 plan must (a) replace the
constant with dynamic ``os.path.relpath`` resolution and (b) ship a unit
test exercising at least 3 different ``output_path`` parents
(``examples/``, ``charts/.../files/``, ``/tmp/``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
from ruyaml import YAML

from arrconf.client_base import SonarrClient
from arrconf.resources.sonarr.download_client import DownloadClient

log = structlog.get_logger()

# Phase 1: hardcoded relative path from ``examples/<file>.yml`` to the repo-root
# ``schemas/`` directory. See module docstring for the Phase 4 plan.
SCHEMA_RELATIVE_PATH_FROM_EXAMPLES = "../schemas/arrconf-schema.json"

# D-36: Sonarr's privacy stand-in for password / apiKey / userName fields. Dropping
# these from dump output guarantees the round-trip property — committed YAML never
# carries the placeholder, so reload→reconcile has no entry to mishandle, and the
# apply-side merge helper has no work to do for these fields.
REDACTED_VALUE = "***REDACTED***"


def _drop_redacted_fields(dc_dump: dict[str, Any]) -> dict[str, Any]:
    """Drop fields[] entries whose value is REDACTED so dump→apply round-trip stays clean (D-36)."""
    if "fields" not in dc_dump:
        return dc_dump
    dc_dump["fields"] = [f for f in dc_dump["fields"] if f.get("value") != REDACTED_VALUE]
    return dc_dump


def dump_sonarr(client: SonarrClient, output_path: Path) -> None:
    """Fetch current Sonarr download_clients and emit a round-trippable YAML.

    Output format (D-16 modeline as line 1)::

        # yaml-language-server: $schema=../schemas/arrconf-schema.json
        apps:
          sonarr:
            main:
              base_url: <derived from client>
              download_clients:
                prune: false
                items:
                  - name: ...
                    ...
    """
    raw_dcs = client.get("/downloadclient")
    dcs = [DownloadClient.model_validate(x) for x in raw_dcs]
    items_dumped = [_drop_redacted_fields(dc.model_dump(exclude_none=True)) for dc in dcs]
    config_dict: dict[str, Any] = {
        "apps": {
            "sonarr": {
                "main": {
                    "base_url": client.base_url,
                    "download_clients": {
                        "prune": False,
                        "items": items_dumped,
                    },
                }
            }
        }
    }
    modeline = f"# yaml-language-server: $schema={SCHEMA_RELATIVE_PATH_FROM_EXAMPLES}\n"
    # Phase 1 modeline is hardcoded for ``examples/<file>.yml``. If the user
    # writes the dump elsewhere, the relative schema path may not resolve in
    # their editor — surface this as a WARN so the user is informed (vs.
    # discovering a broken modeline silently in their editor). Do NOT change
    # the literal substring "Schema modeline path may not resolve" — a
    # downstream acceptance criterion greps for it.
    try:
        output_parent_resolved = output_path.resolve().parent
        schema_target = (output_parent_resolved / SCHEMA_RELATIVE_PATH_FROM_EXAMPLES).resolve()
        if not schema_target.exists():
            log.warning(
                "schema_modeline_path_unresolved",
                output=str(output_path),
                expected_schema_at=str(schema_target),
                hint=("Schema modeline path may not resolve in editor — schema located at <abs>"),
            )
    except OSError as e:
        log.warning("schema_modeline_path_check_failed", error=str(e))

    yaml = YAML(typ="safe")
    yaml.default_flow_style = False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        f.write(modeline)
        yaml.dump(config_dict, f)
