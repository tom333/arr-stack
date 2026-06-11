"""ruyaml round-trip MUST preserve comments + blank lines + modeline.

Tests run against the dedicated comment-rich fixture
``tests/fixtures/roundtrip_sample.yml`` — NOT the canonical arrconf.yml,
which is 100% generated since Phase 32 and carries no hand comments.
"""

from __future__ import annotations

from pathlib import Path

from arrconf_ui.io import dump_yaml_to_str, read_yaml, write_yaml_atomic


def test_modeline_preserved_on_round_trip(roundtrip_sample: Path) -> None:
    data = read_yaml(roundtrip_sample)
    write_yaml_atomic(roundtrip_sample, data)
    content = roundtrip_sample.read_text(encoding="utf-8")
    # Line 1 of the sample is `# yaml-language-server: $schema=...`
    assert content.splitlines()[0].startswith("# yaml-language-server:")


def test_section_comments_preserved(roundtrip_sample: Path) -> None:
    """Comment blocks (decision markers) survive round-trip."""
    data = read_yaml(roundtrip_sample)
    write_yaml_atomic(roundtrip_sample, data)
    content = roundtrip_sample.read_text(encoding="utf-8")
    assert "D-06-SCOPE-01" in content
    assert "D-07-INSTANCE-01" in content
    assert "ADR-8" in content


def test_atomic_write_no_corruption_on_failure(tmp_path: Path) -> None:
    """If write fails mid-stream, original file MUST be intact."""
    target = tmp_path / "arrconf.yml"
    target.write_text("categories: []\n", encoding="utf-8")

    # Try to dump an object that cannot be serialized; atomic write must
    # NOT clobber the original file.
    class Unserializable:
        pass

    try:
        write_yaml_atomic(target, {"bad": Unserializable()})
    except Exception:
        pass

    # File still exists with original content.
    assert target.read_text(encoding="utf-8") == "categories: []\n"

    # No leftover .tmp files.
    tmp_files = list(tmp_path.glob(".arrconf.yml.*.tmp"))
    assert tmp_files == [], f"leaked tmp files: {tmp_files}"


def test_dump_yaml_to_str_is_utf8(roundtrip_sample: Path) -> None:
    """Émilie / Garçons / Zoé accented strings survive dump."""
    data = read_yaml(roundtrip_sample)
    out = dump_yaml_to_str(data)
    assert "Émilie" in out
    assert "Garçons" in out
    assert "Zoé" in out
