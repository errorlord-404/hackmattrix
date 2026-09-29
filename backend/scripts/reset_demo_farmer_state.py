"""Delete only the explicitly selected local demo farmer SQLite database."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import settings
from app.farm_state.store import safe_farmer_key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--farmer-id", default="demo")
    parser.add_argument("--confirm-demo-reset", action="store_true")
    args = parser.parse_args()
    if not args.confirm_demo_reset:
        raise SystemExit("Refusing to delete farmer data without --confirm-demo-reset")
    farmer_id = safe_farmer_key(args.farmer_id)
    directory = Path(settings.FARM_STATE_DB_DIR).expanduser()
    if not directory.is_absolute():
        directory = Path(__file__).resolve().parents[1] / directory
    target = directory / f"{farmer_id}.sqlite3"
    if target.exists():
        target.unlink()
        print(f"Reset local demo farmer store: {farmer_id}")
    else:
        print(f"Local demo farmer store was already clean: {farmer_id}")


if __name__ == "__main__":
    main()
