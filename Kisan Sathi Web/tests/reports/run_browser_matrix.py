from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    project = f"kisansathi-gate-{os.getpid()}"
    port_base = 18000 + (os.getpid() % 500)
    env = os.environ.copy()
    env.update({"API_PORT": str(port_base), "WEB_PORT": str(port_base + 80)})
    compose = [
        "docker",
        "compose",
        "--project-name",
        project,
        "--env-file",
        "deploy/.env.example",
        "--profile",
        "test",
        "-f",
        "deploy/compose.yaml",
    ]
    up = compose + [
        "up",
        "--build",
        "--abort-on-container-exit",
        "--exit-code-from",
        "browser-tests",
        "--no-log-prefix",
    ]
    down = compose + ["down"]
    completed = subprocess.run(up, cwd=ROOT, env=env, check=False)
    cleanup = subprocess.run(down, cwd=ROOT, env=env, check=False, capture_output=True, text=True)
    if cleanup.returncode:
        print(cleanup.stdout, file=sys.stdout)
        print(cleanup.stderr, file=sys.stderr)
    return completed.returncode or cleanup.returncode


if __name__ == "__main__":
    raise SystemExit(main())
