"""Tag-preserving read helper for configarr.yml (SC#4 / T-25-01).

ruyaml round-trip mode keeps ``!env`` / ``!secret`` tagged scalars as
``TaggedScalar`` objects in memory.  When callers need a plain ``dict``
representation (e.g. for the GET /api/configarr endpoint), a naïve
``json.loads(json.dumps(raw, default=str))`` round-trip silently drops
the tag — ``str(TaggedScalar)`` returns only ``.value``, so
``"!env SONARR_API_KEY"`` becomes ``"SONARR_API_KEY"`` (Pitfall 1,
D-04).

``_tagged_to_literal`` walks the tree and reconstructs the full literal
(``"!env SONARR_API_KEY"``) from ``node.tag.value + " " + node.value``.
All other scalars pass through unchanged.
"""

from __future__ import annotations

from typing import Any

from ruyaml.comments import TaggedScalar


def _tagged_to_literal(node: Any) -> Any:
    """Recursively convert TaggedScalars to their literal string representation.

    For a TaggedScalar ``!env SONARR_API_KEY``:
      ``node.tag.value``  == ``"!env"``
      ``node.value``      == ``"SONARR_API_KEY"``
    Result: ``"!env SONARR_API_KEY"`` — the literal tag reference, NOT the
    resolved env value (safe to surface on the API per D-04 / T-25-03).

    Non-tagged scalars (str, int, float, bool, None) are returned as-is.
    """
    if isinstance(node, TaggedScalar):
        return f"{node.tag.value} {node.value}"
    if isinstance(node, dict):
        return {k: _tagged_to_literal(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_tagged_to_literal(v) for v in node]
    return node
