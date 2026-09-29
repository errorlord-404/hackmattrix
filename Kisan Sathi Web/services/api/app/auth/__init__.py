"""Authentication boundary for web requests."""
"""API authentication boundary."""

from pathlib import Path
import sys


_source = Path(__file__).resolve()
_root_candidates = [*_source.parents, Path.cwd(), Path.cwd().parent]
_standalone_root = next(
    (candidate for candidate in _root_candidates if (candidate / "packages" / "auth" / "kisansathi_auth").is_dir()),
    _source.parents[2],
)
_AUTH_PACKAGE = _standalone_root / "packages" / "auth"
if str(_AUTH_PACKAGE) not in sys.path:
    sys.path.insert(0, str(_AUTH_PACKAGE))
