"""Sonarr/Radarr HostConfig pydantic schema — singleton GET/PUT.

Returned by ``GET /api/v3/config/host`` as a flat object (NOT a list, NOT a
``fields[]``-bearing resource). The reconciler pattern is:
    GET current -> diff against desired -> PUT if different (with ?forceSave=true).

Credential fields (``apiKey``, ``password``, ``passwordConfirmation``,
``username``) are EXCLUDED with ``exclude=True`` — they MUST NEVER appear in
diff output or PUT body. Writing the API key from YAML would overwrite the
app's own auth credentials from the config file — a security risk equivalent
to bypassing ADR-5 scope.

The host_config reconciler ALSO checks ``HostConfigSection.enable`` before
calling GET / PUT (D-03-04 opt-in safety guard — added in Plan 02).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HostConfig(BaseModel):
    """Sonarr/Radarr singleton host configuration (UI access control, port, urlBase, ...).

    Writable subset (safe to reconcile from YAML):
      - authenticationMethod, authenticationRequired
      - bindAddress, port, urlBase, instanceName

    Excluded (NEVER write back from YAML):
      - id (server-assigned, re-injected by reconciler after merge)
      - apiKey, password, passwordConfirmation, username (credentials --
        D-03-04 / Pitfall 4 / RESEARCH.md §4)
      - branch (Sonarr's branch tracking -- out of YAML scope)
    """

    model_config = ConfigDict(extra="allow")

    # Writable fields:
    authenticationMethod: str | None = None
    authenticationRequired: str | None = None
    bindAddress: str | None = None
    port: int | None = None
    urlBase: str | None = None
    instanceName: str | None = None
    # Read-only / credential — NEVER write from YAML (D-03-04 / RESEARCH.md §4):
    id: int | None = Field(default=None, exclude=True)
    apiKey: str | None = Field(default=None, exclude=True)
    password: str | None = Field(default=None, exclude=True)
    passwordConfirmation: str | None = Field(default=None, exclude=True)
    username: str | None = Field(default=None, exclude=True)
    branch: str | None = Field(default=None, exclude=True)
