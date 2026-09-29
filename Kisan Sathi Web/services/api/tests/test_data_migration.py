from __future__ import annotations

import json

import pytest

from app.farm_state.store import FarmStateStore
from scripts.migrate_data import MigrationError, export_bundle, import_bundle, rehearse


def _seed(store: FarmStateStore) -> None:
    store.execute("INSERT INTO profile(id,name,preferred_language,created_at,updated_at) VALUES(?,?,?,?,?)", (store.farmer_id, "Asha", "en", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"))
    store.execute("INSERT INTO fields(id,name,area_acres,boundary_geojson,status,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)", ("field-1", "North", 2, '{"type":"Polygon","coordinates":[]}', "unknown", 1, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"))


def test_export_import_is_tenant_partitioned_checksum_checked_and_reconcilable(tmp_path):
    source = FarmStateStore(farmer_id="farmer-a", tenant_id="tenant-a", db_dir=tmp_path / "source")
    _seed(source)
    bundle = tmp_path / "bundle.json"
    exported = export_bundle(source, bundle, backup_id="backup-001")
    assert exported["status"] == "exported"
    document = json.loads(bundle.read_text(encoding="utf-8"))
    assert "ledger_entries" not in document["tables"]
    target = FarmStateStore(farmer_id="farmer-a", tenant_id="tenant-a", db_dir=tmp_path / "target")
    imported = import_bundle(bundle, target, backup_id="backup-001")
    assert imported["status"] == "imported"
    assert imported["inserted"]["fields"] == 1
    rerun = import_bundle(bundle, target, backup_id="backup-001")
    assert rerun["inserted"]["fields"] == 0
    rehearsal = rehearse(source, tmp_path / "rehearsal")
    assert rehearsal["status"] == "rehearsed"
    assert rehearsal["reconciliation"]["counts_match"] is True
    target.close(); source.close()


def test_import_scope_checksum_and_transaction_rollback(tmp_path):
    source = FarmStateStore(farmer_id="farmer-a", tenant_id="tenant-a", db_dir=tmp_path / "source")
    _seed(source); bundle = tmp_path / "bundle.json"; export_bundle(source, bundle)
    tampered = json.loads(bundle.read_text(encoding="utf-8")); tampered["tables"]["fields"][0]["name"] = "tampered"; bundle.write_text(json.dumps(tampered), encoding="utf-8")
    target = FarmStateStore(farmer_id="farmer-a", tenant_id="tenant-a", db_dir=tmp_path / "target")
    with pytest.raises(MigrationError, match="checksum"):
        import_bundle(bundle, target)
    export_bundle(source, bundle)
    wrong_scope = FarmStateStore(farmer_id="farmer-b", tenant_id="tenant-a", db_dir=tmp_path / "wrong")
    with pytest.raises(MigrationError, match="scope"):
        import_bundle(bundle, wrong_scope)
    wrong_scope.close()
    malformed = json.loads(bundle.read_text(encoding="utf-8")); malformed["tables"]["fields"][0]["unknown"] = "x"; unsigned = {key: value for key, value in malformed.items() if key != "checksum"}; import hashlib; malformed["checksum"] = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest(); bundle.write_text(json.dumps(malformed), encoding="utf-8")
    with pytest.raises(MigrationError, match="unknown columns"):
        import_bundle(bundle, target)
    assert target.one("SELECT COUNT(*) count FROM fields")["count"] == 0
    target.close(); source.close()
