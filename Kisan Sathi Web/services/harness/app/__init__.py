"""Standalone provider-neutral web harness package."""

from pathlib import Path
import sys


_source = Path(__file__).resolve()
_ROOT = next(
    (candidate for candidate in [*_source.parents, Path.cwd(), Path.cwd().parent] if (candidate / "packages" / "auth").is_dir()),
    _source.parents[2],
)
for _package in (_ROOT / "packages" / "auth", _ROOT / "packages" / "tool-registry"):
    if str(_package) not in sys.path:
        sys.path.insert(0, str(_package))
