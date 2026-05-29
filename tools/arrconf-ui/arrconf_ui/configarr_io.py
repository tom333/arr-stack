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


def count_secret_tags(node: Any) -> int:
    """Count ``!env``/``!secret`` ``TaggedScalar`` nodes in a ruyaml tree (D-09).

    Counts actual tag *nodes*, NOT text substrings. A plain string
    ``"!env SONARR_API_KEY"`` (a demoted/leaked secret reference) contains the
    substring ``!env`` but is NOT a tag node — it must not count toward the
    total. The previous substring-based guard let tag demotion slip past
    silently (CR-01): wholesale-replacing a ``sonarr`` block with a JSON payload
    re-quotes ``api_key`` as a plain string whose text still holds ``!env``, so
    a ``.count("!env")`` check never fired.
    """
    if isinstance(node, TaggedScalar):
        return 1 if node.tag.value in ("!env", "!secret") else 0
    if isinstance(node, dict):
        return sum(count_secret_tags(v) for v in node.values())
    if isinstance(node, list):
        return sum(count_secret_tags(v) for v in node)
    return 0


def merge_preserving_tags(target: Any, payload: Any) -> None:
    """Deep-merge ``payload`` into a ruyaml ``target`` tree, in place.

    Existing ``TaggedScalar`` values (e.g. ``!env SONARR_API_KEY``) are NEVER
    overwritten by the payload's plain-string echo — they are readOnly secret
    references (D-04) that the round-trip must keep as YAML *tags*, not demote
    to quoted strings (CR-01 / SC#4). All other leaves are taken from
    ``payload``; nested dicts recurse so deeply-nested tags survive too.

    Lists are replaced wholesale: configarr's editable collections
    (``quality_profiles``, ``custom_formats``, ...) carry no secret tags. The
    D-09 ``count_secret_tags`` guard is the backstop if that assumption ever
    breaks.
    """
    if not isinstance(target, dict) or not isinstance(payload, dict):
        return
    for key, new_val in payload.items():
        existing = target.get(key)
        if isinstance(existing, TaggedScalar):
            continue  # preserve the secret tag node — never take the plain echo
        if isinstance(existing, dict) and isinstance(new_val, dict):
            merge_preserving_tags(existing, new_val)
        else:
            target[key] = new_val
