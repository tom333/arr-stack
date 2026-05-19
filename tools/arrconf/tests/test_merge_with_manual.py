"""Unit tests for arrconf.reconcilers._shared.merge_with_manual (D-02).

Three behavioural cases covering the per-resource toggle:
- manual non-empty → manual wins, generated skipped
- manual empty → generated wins
- both empty → empty list returned (edge case)
"""

from __future__ import annotations

import logging

import pytest
import structlog

from arrconf.reconcilers._shared import merge_with_manual


@pytest.fixture(autouse=True)
def configure_structlog_capture(caplog: pytest.LogCaptureFixture) -> None:
    """Route structlog output through the standard logger so caplog can capture it.

    Note: structlog in the arrconf project is wired in arrconf.logging.configure_logging().
    For tests we keep the default ProcessorFormatter pass-through so log records carry
    the structured kv pairs as attributes on the LogRecord (structlog >= 23).
    """
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
