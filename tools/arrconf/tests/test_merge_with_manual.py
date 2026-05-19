"""Unit tests for arrconf.reconcilers._shared.merge_with_manual (D-02).

Three behavioural cases covering the per-resource toggle:
- manual non-empty → manual wins, generated skipped
- manual empty → generated wins
- both empty → empty list returned (edge case)
"""

from __future__ import annotations

import logging
from collections.abc import Generator

import pytest
import structlog
import structlog._config as _sc

from arrconf.reconcilers._shared import merge_with_manual


@pytest.fixture(autouse=True)
def configure_structlog_capture(caplog: pytest.LogCaptureFixture) -> Generator[None]:
    """Route structlog output through the standard logger so caplog can capture it.

    Note: structlog in the arrconf project is wired in arrconf.logging.configure_logging().
    For tests we keep the default ProcessorFormatter pass-through so log records carry
    the structured kv pairs as attributes on the LogRecord (structlog >= 23).

    Uses structlog.reset_defaults() before reconfiguring to clear any cached bound
    loggers set by a prior test (e.g. test_cli.py calls configure_logging() with
    cache_logger_on_first_use=True, caching a JSON-to-stdout chain; without the reset
    the caplog handler never receives the log records).

    Yields so the teardown block restores the original structlog configuration AND
    the original module-level ``log`` in _shared.py, preventing this fixture from
    breaking tests in other modules that run after test_merge_with_manual.py
    (e.g. test_reconcilers_jellyfin.py::test_reconcile_jellyfin_step_order_invariant
    uses structlog.testing.capture_logs() which requires the pre-configured structlog
    chain from configure_logging(), not the stdlib chain set here).
    """
    import arrconf.reconcilers._shared as _shared_mod

    # Save original _shared.log binding before patching.
    original_log = _shared_mod.log

    # Save a snapshot of the original structlog _Configuration state so we can
    # restore it exactly after these tests. The _Configuration object stores the
    # active config fields as instance attributes.
    original_config = {
        "default_processors": _sc._CONFIG.default_processors,
        "default_context_class": _sc._CONFIG.default_context_class,
        "default_wrapper_class": _sc._CONFIG.default_wrapper_class,
        "logger_factory": _sc._CONFIG.logger_factory,
        "cache_logger_on_first_use": _sc._CONFIG.cache_logger_on_first_use,
    }

    # Reconfigure structlog to route through stdlib so caplog can capture.
    structlog.reset_defaults()
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.KeyValueRenderer(key_order=["event"]),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )
    caplog.set_level(logging.INFO)

    # Patch the module-level log in _shared to a fresh BoundLogger that binds to
    # the newly configured stdlib LoggerFactory (cache_logger_on_first_use=False
    # ensures the next get_logger() call re-evaluates the factory).
    _shared_mod.log = structlog.get_logger()

    yield

    # Teardown: restore original _shared.log so other test files are not affected.
    _shared_mod.log = original_log

    # Restore original structlog configuration exactly so tests that run after this
    # file and use structlog.testing.capture_logs() work correctly.
    structlog.reset_defaults()
    _sc._CONFIG.default_processors = original_config["default_processors"]
    _sc._CONFIG.default_context_class = original_config["default_context_class"]
    _sc._CONFIG.default_wrapper_class = original_config["default_wrapper_class"]
    _sc._CONFIG.logger_factory = original_config["logger_factory"]
    _sc._CONFIG.cache_logger_on_first_use = original_config["cache_logger_on_first_use"]
    # Re-mark as configured if it was configured before (so subsequent tests that
    # call configure_logging() don't silently skip due to already-configured guard).
    _sc._CONFIG.is_configured = True


def test_manual_non_empty_wins() -> None:
    """D-02 Behaviour A: manual list survives, generated discarded."""
    result = merge_with_manual([1, 2, 3], [10, 20, 30, 40], app="sonarr", resource="tags")
    assert result == [1, 2, 3]


def test_manual_empty_uses_generated() -> None:
    """D-02 Behaviour B: empty manual → Categories-derived list takes effect."""
    result = merge_with_manual([], [10, 20, 30], app="sonarr", resource="root_folders")
    assert result == [10, 20, 30]


def test_both_empty_returns_empty() -> None:
    """Edge case: nothing to merge → empty list."""
    result = merge_with_manual([], [], app="qbit", resource="categories")
    assert result == []


def test_log_event_manual_wins(caplog: pytest.LogCaptureFixture) -> None:
    """Manual-wins emits source='manual', n=<manual len>, generated_skipped=<generated len>."""
    merge_with_manual(["a", "b"], ["x", "y", "z"], app="sonarr", resource="download_clients")
    matching = [r for r in caplog.records if "merge_decision" in r.getMessage()]
    record_msgs = [r.getMessage() for r in caplog.records]
    assert matching, f"merge_decision event not logged; got records: {record_msgs}"
    msg = matching[-1].getMessage()
    # KeyValueRenderer quotes string values: source='manual'
    assert "source='manual'" in msg
    assert "n=2" in msg
    assert "generated_skipped=3" in msg


def test_log_event_generated_wins(caplog: pytest.LogCaptureFixture) -> None:
    """Generated-wins emits source='categories', n=<generated len>."""
    merge_with_manual([], ["x", "y", "z"], app="sonarr", resource="tags")
    matching = [r for r in caplog.records if "merge_decision" in r.getMessage()]
    record_msgs = [r.getMessage() for r in caplog.records]
    assert matching, f"merge_decision event not logged; got records: {record_msgs}"
    msg = matching[-1].getMessage()
    # KeyValueRenderer quotes string values: source='categories'
    assert "source='categories'" in msg
    assert "n=3" in msg


def test_app_and_resource_are_keyword_only() -> None:
    """Signature enforces explicit keyword usage to prevent ambiguous call sites."""
    with pytest.raises(TypeError):
        merge_with_manual([], [], "sonarr", "tags")  # type: ignore[misc]
