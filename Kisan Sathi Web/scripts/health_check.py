from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deploy.health.check import DeploymentContractError, validate_compose


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the standalone deployment contract")
    parser.add_argument("--compose", type=Path, required=True)
    parser.add_argument("--config-only", action="store_true", help="validate topology without contacting services")
    args = parser.parse_args()
    try:
        validate_compose(args.compose.resolve())
    except (DeploymentContractError, OSError) as exc:
        print(f"deployment health contract: FAIL: {exc}")
        return 1
    print("deployment health contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
