from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path


REQUIRED_KEYS = ("release_id", "image_identity", "schema_identity", "model_identity", "data_identity")


class RollbackError(RuntimeError):
    pass


def validate_target(target: dict) -> None:
    missing = [key for key in REQUIRED_KEYS if not target.get(key)]
    if missing:
        raise RollbackError(f"rollback target is missing: {', '.join(missing)}")
    if any(".." in str(value).replace("\\", "/").split("/") for value in target.values()):
        raise RollbackError("rollback identity contains a parent path")


def apply_rollback(state_path: Path, target_path: Path, *, dry_run: bool) -> dict:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    target = json.loads(target_path.read_text(encoding="utf-8"))
    validate_target(target)
    result = {"status": "dry_run" if dry_run else "applied", "previous": state, "target": target}
    if dry_run:
        return result
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=state_path.parent, delete=False) as handle:
        json.dump(target, handle, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, state_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Rehearse or apply a standalone release rollback")
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        result = apply_rollback(args.state.resolve(), args.target.resolve(), dry_run=args.dry_run)
    except (RollbackError, OSError, json.JSONDecodeError) as exc:
        print(f"rollback: FAIL: {exc}")
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
