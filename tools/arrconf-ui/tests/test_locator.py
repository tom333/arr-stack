"""Repo-root + arrconf.yml + schema path locator (D-12)."""

from __future__ import annotations

from arrconf_ui.locator import arrconf_yml_path, repo_root, schema_json_path


def test_repo_root_contains_pyproject() -> None:
    root = repo_root()
    assert (root / "tools" / "arrconf").is_dir()
    assert (root / "tools" / "arrconf-ui").is_dir()
    assert (root / "charts" / "arr-stack").is_dir()


def test_arrconf_yml_path_exists() -> None:
    p = arrconf_yml_path()
    assert p.exists()
    assert p.name == "arrconf.yml"
    assert p.parent.name == "files"


def test_schema_json_path_exists() -> None:
    p = schema_json_path()
    assert p.exists()
    assert p.name == "arrconf-schema.json"


def test_paths_are_absolute() -> None:
    assert arrconf_yml_path().is_absolute()
    assert schema_json_path().is_absolute()
    assert repo_root().is_absolute()
