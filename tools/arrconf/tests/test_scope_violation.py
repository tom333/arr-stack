"""Tests for D-12 ScopeViolationError — frontière configarr (ADR-5).

These tests harden T-01-05: scope-guard bypass would let arrconf overwrite
TRaSH-Guides quality profiles. Each frontière module MUST raise
ScopeViolationError BEFORE any httpx call could possibly happen.
"""

from __future__ import annotations

from types import ModuleType

import pytest
import respx

from arrconf.exceptions import ScopeViolationError
from arrconf.resources.radarr import (
    custom_format as radarr_custom_format,
)
from arrconf.resources.radarr import (
    media_naming as radarr_media_naming,
)
from arrconf.resources.radarr import (
    quality_definition as radarr_quality_definition,
)
from arrconf.resources.radarr import (
    quality_profile as radarr_quality_profile,
)
from arrconf.resources.sonarr import (
    custom_format,
    media_naming,
    quality_definition,
    quality_profile,
)

FRONTIERE_MODULES: list[ModuleType] = [
    # Sonarr frontière (REQ-configarr-coexistence — original):
    quality_profile,
    custom_format,
    quality_definition,
    media_naming,
    # Radarr frontière (REQ-configarr-coexistence — Phase 3 / D-03-01):
    radarr_quality_profile,
    radarr_custom_format,
    radarr_quality_definition,
    radarr_media_naming,
]


@pytest.mark.parametrize("module", FRONTIERE_MODULES, ids=lambda m: m.__name__.split(".")[-1])
def test_scope_violation_raised_with_configarr_message(module: ModuleType) -> None:
    """Each frontière module raises ScopeViolationError mentioning configarr.yml (D-12)."""
    with pytest.raises(ScopeViolationError, match=r"configarr\.yml"):
        module.reconcile(client=None, config=None, dry_run=False)


@pytest.mark.parametrize("module", FRONTIERE_MODULES, ids=lambda m: m.__name__.split(".")[-1])
@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_scope_violation_raises_BEFORE_any_http_call(  # noqa: N802 (T-01-05 emphasis)
    respx_mock: respx.MockRouter,
    module: ModuleType,
) -> None:
    """T-01-05 mitigation: ScopeViolationError must raise pre-network.

    Even if a future bug introduced httpx into the frontière modules,
    this test catches it: respx records ALL calls. If any route is hit,
    the assertion ``respx_mock.calls.call_count == 0`` fails.
    """
    # Intentionally do NOT register any routes — any call would surface as
    # an unhandled-route error before the assertion would even fire.
    with pytest.raises(ScopeViolationError):
        module.reconcile(client=None, config=None, dry_run=False)
    # Hard assertion: zero HTTP calls were recorded.
    assert respx_mock.calls.call_count == 0, (
        f"{module.__name__}: ScopeViolationError raised, but {respx_mock.calls.call_count} "
        f"HTTP calls were attempted. T-01-05 violated."
    )


@pytest.mark.parametrize("module", FRONTIERE_MODULES, ids=lambda m: m.__name__.split(".")[-1])
def test_scope_violation_message_names_resource(module: ModuleType) -> None:
    """Error message must name the specific resource type for actionable error reporting."""
    resource_name = module.__name__.split(".")[-1]
    # Allow either the singular ("media_naming") or the plural form ("quality_profiles").
    plural = resource_name + "s" if not resource_name.endswith("s") else resource_name
    with pytest.raises(ScopeViolationError) as exc:
        module.reconcile(client=None, config=None, dry_run=False)
    msg = str(exc.value)
    assert resource_name in msg or plural in msg, (
        f"Error message must mention '{resource_name}' or '{plural}': {msg}"
    )
