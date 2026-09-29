from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from app.core.config import settings


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def json_text(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def json_value(value: str | None, default: Any = None) -> Any:
    if value is None:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def request_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def get_idempotent_response(store: "FarmStateStore", key: str | None, payload: Any) -> Any | None:
    if not key:
        return None
    if not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", key):
        raise ValueError("Idempotency-Key must contain 8-160 safe characters")
    row = store.one("SELECT request_hash, response_body FROM idempotency_records WHERE key = ?", (key,))
    if not row:
        return None
    if row["request_hash"] != request_hash(payload):
        raise ValueError("Idempotency-Key was already used with a different request")
    return json_value(row["response_body"], {})


def save_idempotent_response(
    store: "FarmStateStore",
    key: str | None,
    payload: Any,
    response_body: Any,
    response_status: int = 200,
) -> None:
    if not key:
        return
    store.execute(
        "INSERT INTO idempotency_records(key, request_hash, response_status, response_body, created_at) VALUES (?, ?, ?, ?, ?)",
        (key, request_hash(payload), response_status, json_text(response_body), iso_now()),
    )


def safe_farmer_key(value: str) -> str:
    normalized = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", normalized):
        raise ValueError("Farmer ID must contain only letters, numbers, '-' or '_'")
    return normalized


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS profile (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT,
    location TEXT,
    preferred_language TEXT NOT NULL DEFAULT 'en',
    latitude REAL,
    longitude REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS preferences (
    profile_id TEXT PRIMARY KEY REFERENCES profile(id) ON DELETE CASCADE,
    notifications_enabled INTEGER NOT NULL DEFAULT 1,
    notification_preferences TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fields (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    area_acres REAL NOT NULL CHECK(area_acres > 0),
    boundary_geojson TEXT NOT NULL,
    centroid_lat REAL,
    centroid_lon REAL,
    current_crop TEXT,
    status TEXT NOT NULL DEFAULT 'unknown',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS crop_cycles (
    id TEXT PRIMARY KEY,
    field_id TEXT NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    crop_name TEXT NOT NULL,
    planted_at TEXT NOT NULL,
    expected_harvest_date TEXT,
    current_stage TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS crop_stage_events (
    id TEXT PRIMARY KEY,
    crop_cycle_id TEXT NOT NULL REFERENCES crop_cycles(id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS field_tasks (
    id TEXT PRIMARY KEY,
    field_id TEXT NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    due_at TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    source TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS harvest_lots (
    id TEXT PRIMARY KEY,
    crop_cycle_id TEXT NOT NULL REFERENCES crop_cycles(id) ON DELETE CASCADE,
    field_id TEXT NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    harvested_on TEXT NOT NULL,
    quantity REAL NOT NULL CHECK(quantity > 0),
    unit TEXT NOT NULL CHECK(unit IN ('kg', 'quintal', 'tonne')),
    grade TEXT,
    storage_note TEXT,
    final_harvest INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'farmer_reported',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ledger_entries (
    id TEXT PRIMARY KEY,
    field_id TEXT REFERENCES fields(id) ON DELETE SET NULL,
    entry_type TEXT NOT NULL CHECK(entry_type IN ('income', 'expense')),
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    amount_inr REAL NOT NULL CHECK(amount_inr > 0),
    occurred_at TEXT NOT NULL,
    crop_name TEXT,
    note TEXT,
    source TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'void')),
    created_at TEXT NOT NULL,
    voided_at TEXT
);
CREATE TABLE IF NOT EXISTS device_telemetry_packets (
    id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    field_id TEXT NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    boot_id TEXT NOT NULL,
    sequence INTEGER NOT NULL CHECK(sequence >= 0),
    observed_at TEXT NOT NULL,
    received_at TEXT NOT NULL,
    firmware_version TEXT NOT NULL,
    transport TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL CHECK(status IN ('accepted', 'rejected')),
    rejection_reason TEXT,
    UNIQUE(device_id, boot_id, sequence)
);
CREATE TABLE IF NOT EXISTS device_telemetry_samples (
    id TEXT PRIMARY KEY,
    packet_id TEXT NOT NULL REFERENCES device_telemetry_packets(id) ON DELETE CASCADE,
    probe_id TEXT NOT NULL,
    measurement TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    modbus_address INTEGER NOT NULL CHECK(modbus_address BETWEEN 1 AND 247),
    crc_ok INTEGER NOT NULL,
    quality_status TEXT NOT NULL,
    calibration_revision TEXT,
    rejection_reason TEXT
);
CREATE TABLE IF NOT EXISTS soil_tests (
    id TEXT PRIMARY KEY,
    field_id TEXT NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    observed_at TEXT NOT NULL,
    ph REAL,
    organic_carbon REAL,
    nitrogen REAL,
    phosphorus REAL,
    potassium REAL,
    ec REAL,
    moisture_percent REAL,
    source TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    confidence REAL
);
CREATE TABLE IF NOT EXISTS sensor_devices (
    id TEXT PRIMARY KEY,
    field_id TEXT NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    device_type TEXT NOT NULL,
    unit TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sensor_readings (
    id TEXT PRIMARY KEY,
    field_id TEXT NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    device_id TEXT,
    measurement TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    source TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    confidence REAL,
    FOREIGN KEY(device_id) REFERENCES sensor_devices(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS tomato_demo_state (
    field_id TEXT PRIMARY KEY REFERENCES fields(id) ON DELETE CASCADE,
    running INTEGER NOT NULL DEFAULT 0,
    scenario TEXT NOT NULL,
    seed INTEGER NOT NULL,
    tick_count INTEGER NOT NULL DEFAULT 0,
    values_json TEXT NOT NULL,
    irrigation_ticks_remaining INTEGER NOT NULL DEFAULT 0,
    observed_at TEXT,
    last_tick_at TEXT,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS field_observations (
    id TEXT PRIMARY KEY,
    field_id TEXT NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    observation_type TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    source TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    confidence REAL
);
CREATE TABLE IF NOT EXISTS irrigation_plans (
    id TEXT PRIMARY KEY,
    field_id TEXT NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    recommended_window_start TEXT,
    recommended_window_end TEXT,
    target_moisture_percent REAL NOT NULL,
    estimated_volume_liters REAL,
    estimated_duration_minutes REAL,
    status TEXT NOT NULL DEFAULT 'recommended',
    explanation TEXT NOT NULL,
    assumptions TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS irrigation_events (
    id TEXT PRIMARY KEY,
    field_id TEXT NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    occurred_at TEXT NOT NULL,
    volume_liters REAL,
    duration_minutes REAL,
    method TEXT,
    note TEXT,
    source TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reminders (
    id TEXT PRIMARY KEY,
    field_id TEXT REFERENCES fields(id) ON DELETE CASCADE,
    reminder_type TEXT NOT NULL,
    scheduled_for TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled',
    title TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS weather_snapshots (
    id TEXT PRIMARY KEY,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    provider TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    payload TEXT NOT NULL,
    freshness_seconds INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS weather_alerts (
    id TEXT PRIMARY KEY,
    field_id TEXT REFERENCES fields(id) ON DELETE CASCADE,
    alert_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT NOT NULL,
    source TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS diagnosis_requests (
    id TEXT PRIMARY KEY,
    field_id TEXT REFERENCES fields(id) ON DELETE SET NULL,
    status TEXT NOT NULL,
    provider TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS media_uploads (
    id TEXT PRIMARY KEY,
    field_id TEXT REFERENCES fields(id) ON DELETE SET NULL,
    path TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    checksum TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'stored_private',
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS media_processing_consents (
    id TEXT PRIMARY KEY,
    upload_id TEXT NOT NULL REFERENCES media_uploads(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    purpose TEXT NOT NULL,
    notice_version TEXT NOT NULL,
    decision TEXT NOT NULL CHECK(decision IN ('approved', 'declined')),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS diagnoses (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES diagnosis_requests(id) ON DELETE CASCADE,
    label TEXT,
    status TEXT NOT NULL,
    confidence REAL,
    severity TEXT,
    treatment TEXT,
    provider_output TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS diagnosis_images (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES diagnosis_requests(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    checksum TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS diagnosis_feedback (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES diagnosis_requests(id) ON DELETE CASCADE,
    confirmed_crop TEXT,
    label TEXT,
    correctness TEXT NOT NULL CHECK(correctness IN ('confirmed', 'corrected', 'unknown')),
    share_for_model_improvement INTEGER NOT NULL DEFAULT 0 CHECK(share_for_model_improvement IN (0, 1)),
    note TEXT,
    reviewer_type TEXT NOT NULL DEFAULT 'farmer',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS disease_events (
    id TEXT PRIMARY KEY,
    field_id TEXT NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    diagnosis_id TEXT REFERENCES diagnoses(id) ON DELETE SET NULL,
    occurred_at TEXT NOT NULL,
    note TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS advisor_sessions (
    id TEXT PRIMARY KEY,
    field_id TEXT REFERENCES fields(id) ON DELETE SET NULL,
    language TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS advisor_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES advisor_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    citations TEXT NOT NULL DEFAULT '[]',
    provider TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recommendations (
    id TEXT PRIMARY KEY,
    field_id TEXT REFERENCES fields(id) ON DELETE SET NULL,
    kind TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    field_id TEXT REFERENCES fields(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    dedupe_key TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notification_deliveries (
    id TEXT PRIMARY KEY,
    alert_id TEXT NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    channel TEXT NOT NULL,
    status TEXT NOT NULL,
    attempted_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    report_type TEXT NOT NULL,
    from_date TEXT,
    to_date TEXT,
    status TEXT NOT NULL,
    input_snapshot TEXT NOT NULL,
    artifact TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS report_jobs (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS idempotency_records (
    key TEXT PRIMARY KEY,
    request_hash TEXT NOT NULL,
    response_status INTEGER NOT NULL,
    response_body TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    entity TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_crop_cycles_field ON crop_cycles(field_id, status);
CREATE INDEX IF NOT EXISTS idx_stage_events_cycle ON crop_stage_events(crop_cycle_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_ledger_entries_field ON ledger_entries(field_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_ledger_entries_status ON ledger_entries(status, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_packets_field ON device_telemetry_packets(field_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_packets_device ON device_telemetry_packets(device_id, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_soil_tests_field ON soil_tests(field_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_sensor_readings_field ON sensor_readings(field_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_observations_field ON field_observations(field_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_weather_snapshots_location ON weather_snapshots(latitude, longitude, fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_field ON alerts(field_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_harvest_lots_field ON harvest_lots(field_id, harvested_on DESC);
CREATE INDEX IF NOT EXISTS idx_diagnosis_feedback_request ON diagnosis_feedback(request_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_media_uploads_field ON media_uploads(field_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_media_uploads_checksum ON media_uploads(checksum);
CREATE INDEX IF NOT EXISTS idx_media_consents_upload ON media_processing_consents(upload_id, provider, purpose, expires_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_created ON audit_events(created_at DESC);
"""


class FarmStateStore:
    """Small repository wrapper around one farmer-owned SQLite database."""

    def __init__(self, farmer_key: str, db_dir: str | Path | None = None):
        self.farmer_key = safe_farmer_key(farmer_key)
        configured_dir = Path(db_dir or settings.FARM_STATE_DB_DIR).expanduser()
        if not configured_dir.is_absolute():
            configured_dir = Path.cwd() / configured_dir
        configured_dir.mkdir(parents=True, exist_ok=True)
        self.path = configured_dir / f"{self.farmer_key}.sqlite3"
        self.connection = sqlite3.connect(self.path, timeout=10, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)
        self.connection.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
            (1, iso_now()),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        cursor = self.connection.execute(sql, tuple(params))
        statement = sql.strip().upper()
        if not statement.startswith("PRAGMA") and not statement.startswith("SELECT") and "AUDIT_EVENTS" not in statement:
            match = re.search(r"\b(?:INTO|UPDATE|FROM)\s+([A-Z_][A-Z0-9_]*)", statement)
            entity = match.group(1).lower() if match else "farm_state"
            action = statement.split(" ", 1)[0].lower()
            self.connection.execute(
                "INSERT INTO audit_events(id, action, entity, created_at) VALUES (?, ?, ?, ?)",
                (str(uuid4()), action, entity, iso_now()),
            )
        self.connection.commit()
        return cursor

    def executemany(self, sql: str, rows: Iterable[Iterable[Any]]) -> None:
        self.connection.executemany(sql, rows)
        self.connection.commit()

    def one(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
        return self.connection.execute(sql, tuple(params)).fetchone()

    def all(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        return self.connection.execute(sql, tuple(params)).fetchall()

    def transaction(self):
        return self.connection
