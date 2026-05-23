"""ruyaml round-trip MUST preserve comments + blank lines + modeline."""

from __future__ import annotations

from pathlib import Path

from arrconf_ui.io import dump_yaml_to_str, read_yaml, write_yaml_atomic


def test_modeline_preserved_on_round_trip(sandboxed_arrconf_yml: Path) -> None:
    data = read_yaml(sandboxed_arrconf_yml)
    write_yaml_atomic(sandboxed_arrconf_yml, data)
    content = sandboxed_arrconf_yml.read_text(encoding="utf-8")
    # Line 1 of canonical arrconf.yml is `# yaml-language-server: $schema=...`
    assert content.splitlines()[0].startswith("# yaml-language-server:")


def test_phase_6_section_comments_preserved(sandboxed_arrconf_yml: Path) -> None:
    """The Phase 6 Seerr comment block (D-06-SCOPE-01 ...) survives round-trip."""
    data = read_yaml(sandboxed_arrconf_yml)
    write_yaml_atomic(sandboxed_arrconf_yml, data)
    content = sandboxed_arrconf_yml.read_text(encoding="utf-8")
    # Spot-check: comments on lines we know exist.
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


def test_dump_yaml_to_str_is_utf8(sandboxed_arrconf_yml: Path) -> None:
    """Émilie / Garçons / Zoé accented strings survive dump."""
    data = read_yaml(sandboxed_arrconf_yml)
    out = dump_yaml_to_str(data)
    assert "Émilie" in out
    assert "Garçons" in out
    assert "Zoé" in out
