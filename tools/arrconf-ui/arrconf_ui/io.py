"""ruyaml round-trip read + atomic write of arrconf.yml (D-05).

Uses `YAML(typ='rt')` (round-trip) NOT `typ='safe'` — preserves comments,
blank lines, and key ordering when writing back. The pydantic validation
happens separately in app.py (PUT handler); this module is pure IO.

Atomic write recipe (D-05 Claude's Discretion):
    1. Write to NamedTemporaryFile in the SAME directory as arrconf.yml.
    2. os.replace(tmp, target) — atomic on POSIX same-filesystem.
    3. On any exception: tmp is cleaned up by the context manager.
"""

from __future__ import annotations

import os
import tempfile
from io import StringIO
from pathlib import Path
from typing import Any

from ruyaml import YAML


def _yaml() -> YAML:
    """Return a configured round-trip YAML parser/emitter."""
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 4096  # avoid line wrapping that breaks long URLs
    return yaml


def read_yaml(path: Path) -> Any:
    """Read a YAML file with round-trip type. Returns ruyaml CommentedMap/CommentedSeq."""
    yaml = _yaml()
    with path.open("r", encoding="utf-8") as f:
        return yaml.load(f)


def dump_yaml_to_str(data: Any) -> str:
    """Dump ruyaml data structure to a UTF-8 string (used for tests + diff preview)."""
    yaml = _yaml()
    buf = StringIO()
    yaml.dump(data, buf)
    return buf.getvalue()


def write_yaml_atomic(path: Path, data: Any) -> None:
    """Atomically write YAML data to ``path``.

    Writes to a temp file in the SAME directory (so os.replace is atomic on
    the same filesystem), then os.replace() swaps it in. On exception the
    temp file is cleaned up by NamedTemporaryFile's context manager.
    """
    yaml = _yaml()
    target_dir = path.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    # delete=False because we close the file before os.replace (Windows-safe
    # pattern; also POSIX-safe). The except branch unlinks on failure.
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(target_dir),
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    try:
        yaml.dump(data, tmp)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, path)
    except Exception:
        tmp.close()
        try:
            os.unlink(tmp.name)
        except FileNotFoundError:
            pass
        raise
