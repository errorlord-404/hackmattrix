from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow the documented direct-script invocation from any working directory
# without importing the parent repository.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.farm_state.store import FarmStateStore, iso_now, json_text, request_hash

FORMAT = "kisansathi-data-bundle-v1"
SCHEMA_VERSION = 1
# Browser-local finance state is deliberately absent. A backend ledger can be
# reintroduced only through a separately approved retention/reconciliation plan.
APPROVED_TABLES = (
    "profile", "preferences", "fields", "crop_cycles", "crop_stage_events",
    "field_tasks", "soil_tests", "sensor_devices", "sensor_readings",
    "field_observations", "irrigation_plans", "irrigation_events", "reminders",
    "weather_snapshots", "weather_alerts", "diagnosis_requests", "diagnoses",
    "diagnosis_images", "diagnosis_feedback", "disease_events", "advisor_sessions",
    "advisor_messages", "alerts", "notification_deliveries", "reports", "report_jobs",
    "audit_events",
)
MAX_ROWS_PER_TABLE = 100_000


class MigrationError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def _checksum(bundle_without_checksum: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(bundle_without_checksum)).hexdigest()


def _validate_bundle(bundle: dict[str, Any]) -> None:
    if bundle.get("format") != FORMAT or bundle.get("schema_version") != SCHEMA_VERSION:
        raise MigrationError("Unsupported migration bundle format or schema version")
    if not isinstance(bundle.get("tenant_id"), str) or not isinstance(bundle.get("farmer_id"), str):
        raise MigrationError("Migration bundle must identify one tenant and farmer scope")
    tables = bundle.get("tables")
    if not isinstance(tables, dict) or set(tables) - set(APPROVED_TABLES):
        raise MigrationError("Bundle contains undeclared or unsupported tables")
    for table, rows in tables.items():
        if not isinstance(rows, list) or len(rows) > MAX_ROWS_PER_TABLE or any(not isinstance(row, dict) for row in rows):
            raise MigrationError(f"Invalid row collection for {table}")
        for row in rows:
            if table == "diagnosis_images":
                path = row.get("path", "")
                if Path(path).is_absolute() or ".." in Path(path).parts:
                    raise MigrationError("Upload metadata contains an unsafe path")
    supplied = bundle.get("checksum")
    unsigned = {key: value for key, value in bundle.items() if key != "checksum"}
    if not isinstance(supplied, str) or supplied != _checksum(unsigned):
        raise MigrationError("Migration bundle checksum does not match its contents")


def export_bundle(store: FarmStateStore, output_path: str | Path, *, dry_run: bool = False, backup_id: str | None = None) -> dict[str, Any]:
    tables = {table: [dict(row) for row in store.all(f"SELECT * FROM [{table}] LIMIT {MAX_ROWS_PER_TABLE}")] for table in APPROVED_TABLES}
    bundle: dict[str, Any] = {
        "format": FORMAT,
        "schema_version": SCHEMA_VERSION,
        "tenant_id": store.tenant_id,
        "farmer_id": store.farmer_id,
        "created_at": iso_now(),
        "backup_id": backup_id or f"export-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "runtime_state_policy": "metadata-only; live databases, upload bytes, caches, and browser-local finance are excluded",
        "tables": tables,
    }
    bundle["checksum"] = _checksum(bundle)
    _validate_bundle(bundle)
    destination = Path(output_path)
    if not dry_run:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(_canonical(bundle))
    return {"status": "dry_run" if dry_run else "exported", "path": str(destination), "checksum": bundle["checksum"], "counts": {table: len(rows) for table, rows in tables.items()}, "backup_id": bundle["backup_id"], "excluded": ["ledger_entries", "live_database_files", "upload_bytes", "browser_local_finance"]}


def _table_columns(store: FarmStateStore, table: str) -> list[str]:
    return [row["name"] for row in store.all(f"PRAGMA table_info([{table}])")]


def _row_key(store: FarmStateStore, table: str, row: dict[str, Any]) -> tuple[Any, ...]:
    columns = _table_columns(store, table); primary = [item["name"] for item in store.all(f"PRAGMA table_info([{table}])") if item["pk"]]
    keys = primary or (["id"] if "id" in columns else columns[:1])
    if any(key not in row for key in keys): raise MigrationError(f"{table} row is missing its primary key")
    return tuple(row[key] for key in keys)


def import_bundle(bundle_path: str | Path, store: FarmStateStore, *, dry_run: bool = False, backup_id: str | None = None) -> dict[str, Any]:
    source = Path(bundle_path)
    try: bundle = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: raise MigrationError("Cannot read migration bundle") from exc
    _validate_bundle(bundle)
    if bundle["tenant_id"] != store.tenant_id or bundle["farmer_id"] != store.farmer_id:
        raise MigrationError("Migration bundle scope does not match the target tenant/farmer store")
    counts = {table: len(rows) for table, rows in bundle["tables"].items()}; inserted = {table: 0 for table in counts}; conflicts: list[str] = []
    if dry_run:
        return {"status": "dry_run", "checksum": bundle["checksum"], "counts": counts, "inserted": inserted, "conflicts": conflicts, "rollback_input": {"backup_id": backup_id or bundle.get("backup_id"), "bundle": str(source)}}
    try:
        with store.transaction() as connection:
            for table in APPROVED_TABLES:
                for row in bundle["tables"].get(table, []):
                    columns = _table_columns(store, table); unknown = set(row) - set(columns)
                    if unknown: raise MigrationError(f"{table} contains unknown columns: {sorted(unknown)}")
                    key = _row_key(store, table, row); existing = connection.execute(f"SELECT * FROM [{table}] WHERE " + " AND ".join(f"[{column}] = ?" for column in ([item["name"] for item in store.all(f"PRAGMA table_info([{table}])") if item["pk"]] or ["id"])), key).fetchone()
                    if existing:
                        if dict(existing) != row: conflicts.append(f"{table}:{key}")
                        continue
                    if not row: continue
                    names = list(row); values = [row[name] for name in names]; connection.execute(f"INSERT INTO [{table}] ({','.join('['+name+']' for name in names)}) VALUES ({','.join('?' for _ in names)})", values); inserted[table] += 1
            if conflicts: raise MigrationError(f"Import conflicts with existing records: {len(conflicts)}")
    except MigrationError:
        raise
    except Exception as exc:
        raise MigrationError("Import failed; transaction rolled back") from exc
    return {"status": "imported", "checksum": bundle["checksum"], "counts": counts, "inserted": inserted, "conflicts": conflicts, "rollback_input": {"backup_id": backup_id or bundle.get("backup_id"), "bundle": str(source)}}


def rehearse(source_store: FarmStateStore, target_root: str | Path, *, backup_id: str = "rehearsal") -> dict[str, Any]:
    target_root = Path(target_root); bundle_path = target_root / "rehearsal.bundle.json"; export = export_bundle(source_store, bundle_path, backup_id=backup_id); target = FarmStateStore(farmer_id=source_store.farmer_id, tenant_id=source_store.tenant_id, db_dir=target_root / "target")
    try:
        imported = import_bundle(bundle_path, target, backup_id=backup_id); source_counts = {table: len([row for row in source_store.all(f"SELECT * FROM [{table}]")]) for table in APPROVED_TABLES}; target_counts = {table: len([row for row in target.all(f"SELECT * FROM [{table}]")]) for table in APPROVED_TABLES};
        if source_counts != target_counts: raise MigrationError("Rehearsal reconciliation counts do not match")
        return {"status": "rehearsed", "export": export, "import": imported, "reconciliation": {"counts_match": True, "source": source_counts, "target": target_counts}}
    finally: target.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export/import a validated Kisan Sathi data bundle")
    sub = parser.add_subparsers(dest="command", required=True)
    export_parser = sub.add_parser("export"); export_parser.add_argument("--tenant-id", required=True); export_parser.add_argument("--farmer-id", required=True); export_parser.add_argument("--db-dir", required=True); export_parser.add_argument("--output", required=True); export_parser.add_argument("--dry-run", action="store_true"); export_parser.add_argument("--backup-id")
    import_parser = sub.add_parser("import"); import_parser.add_argument("--tenant-id", required=True); import_parser.add_argument("--farmer-id", required=True); import_parser.add_argument("--db-dir", required=True); import_parser.add_argument("--bundle", required=True); import_parser.add_argument("--dry-run", action="store_true"); import_parser.add_argument("--backup-id")
    rehearse_parser = sub.add_parser("rehearse"); rehearse_parser.add_argument("--tenant-id", required=True); rehearse_parser.add_argument("--farmer-id", required=True); rehearse_parser.add_argument("--db-dir", required=True); rehearse_parser.add_argument("--output-root", required=True); rehearse_parser.add_argument("--backup-id", default="rehearsal")
    args = parser.parse_args(argv); store = FarmStateStore(farmer_id=args.farmer_id, tenant_id=args.tenant_id, db_dir=args.db_dir)
    try:
        if args.command == "export": result = export_bundle(store, args.output, dry_run=args.dry_run, backup_id=args.backup_id)
        elif args.command == "import": result = import_bundle(args.bundle, store, dry_run=args.dry_run, backup_id=args.backup_id)
        else: result = rehearse(store, args.output_root, backup_id=args.backup_id)
        print(json.dumps(result, indent=2, sort_keys=True)); return 0
    except MigrationError as exc:
        print(json.dumps({"status": "failed", "code": "migration_validation_failed", "message": str(exc)})); return 2
    finally: store.close()


if __name__ == "__main__": sys.exit(main())
