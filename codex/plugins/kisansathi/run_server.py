"""Launch the KisanSathi MCP server without hard-coded developer paths.

During repository development the canonical ``agent/`` package is discovered
next to the fork. A separately installed plugin instead uses the normal
``kisansathi_agent`` Python package, or an explicit trusted
``KISANSATHI_AGENT_ROOT`` override.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    configured_root = os.environ.get("KISANSATHI_AGENT_ROOT")
    repository_agent_root = Path(__file__).resolve().parents[3] / "agent"
    agent_root = Path(configured_root) if configured_root else repository_agent_root
    source_root = agent_root / "src"
    if source_root.is_dir():
        sys.path.insert(0, str(source_root))
    elif configured_root:
        raise SystemExit(
            "KISANSATHI_AGENT_ROOT must point to an agent package root "
            f"containing src/kisansathi_agent (got {agent_root})"
        )
    try:
        from kisansathi_agent.__main__ import main as run_agent
    except ImportError as exc:
        raise SystemExit(
            "Install the KisanSathi MCP package (`python -m pip install -e ./agent`) "
            "or set KISANSATHI_AGENT_ROOT to its source checkout."
        ) from exc

    run_agent()


if __name__ == "__main__":
    main()
