from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator
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
    encoded = json.dumps(value, separators=(",", ":"), sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_idempotency_key(key: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", key):
        raise ValueError("Idempotency-Key must contain 8-160 safe characters")
    return key


def get_idempotent_response(store: "FarmStateStore", key: str | None, payload: Any) -> Any | None:
    if not key:
        return None
    validate_idempotency_key(key)
    row = store.one("SELECT request_hash, response_body FROM idempotency_records WHERE key = ?", (key,))
    if not row:
        return None
    if row["request_hash"] != request_hash(payload):
        raise ValueError("Idempotency-Key was already used with a different request")
    return json_value(row["response_body"], {})


def save_idempotent_response(store: "FarmStateStore", key: str | None, payload: Any, response_body: Any, response_status: int = 200) -> None:
    if not key:
        return
    validate_idempotency_key(key)
    store.connection.execute(
        "INSERT OR IGNORE INTO idempotency_records(key, request_hash, response_status, response_body, created_at) VALUES (?, ?, ?, ?, ?)",
        (key, request_hash(payload), response_status, json_text(response_body), iso_now()),
    )
    store.connection.commit()


def safe_scope_key(value: str) -> str:
    normalized = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,96}", normalized):
        raise ValueError("Scope identifiers must contain only letters, numbers, '.', '-' or '_'")
    return normalized


def safe_farmer_key(value: str) -> str:
    return safe_scope_key(value)


class FarmStateStore:
    """Durable SQLite store for one immutable tenant/farmer scope."""

    def __init__(self, farmer_key: str | None = None, db_dir: str | Path | None = None, *, tenant_id: str = "local", farmer_id: str | None = None, upload_dir: str | Path | None = None):
        resolved_farmer = farmer_id or farmer_key or "demo"
        self.tenant_id = safe_scope_key(tenant_id)
        self.farmer_key = safe_farmer_key(resolved_farmer)
        self.farmer_id = self.farmer_key
        root = Path(db_dir) if db_dir is not None else settings.runtime_db_dir
        root = root.expanduser()
        if not root.is_absolute():
            root = settings._resolve(root)
        root.mkdir(parents=True, exist_ok=True)
        self.root = root
        self.path = root / self.tenant_id / f"{self.farmer_key}.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.upload_dir = Path(upload_dir).expanduser() if upload_dir else settings.runtime_upload_dir
        if not self.upload_dir.is_absolute():
            self.upload_dir = settings._resolve(self.upload_dir)
        self.upload_dir = self.upload_dir / self.tenant_id / self.farmer_key
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, timeout=10, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self._apply_migrations()

    def _apply_migrations(self) -> None:
        migration_dir = Path(__file__).resolve().parents[2] / "migrations"
        for migration in sorted(migration_dir.glob("*.sql")):
            version_match = re.match(r"(\d+)_", migration.name)
            if not version_match:
                continue
            version = int(version_match.group(1))
            table_exists = self.connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'").fetchone()
            if table_exists and self.one("SELECT version FROM schema_migrations WHERE version = ?", (version,)):
                continue
            self.connection.executescript(migration.read_text(encoding="utf-8"))
            self.connection.execute("INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)", (version, iso_now()))
            self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        cursor = self.connection.execute(sql, tuple(params))
        statement = sql.strip().upper()
        if not statement.startswith(("PRAGMA", "SELECT", "WITH")) and "AUDIT_EVENTS" not in statement:
            match = re.search(r"\b(?:INTO|UPDATE|FROM)\s+([A-Z_][A-Z0-9_]*)", statement)
            entity = match.group(1).lower() if match else "farm_state"
            action = statement.split(" ", 1)[0].lower()
            self.connection.execute("INSERT INTO audit_events(id, action, entity, created_at) VALUES (?, ?, ?, ?)", (str(uuid4()), action, entity, iso_now()))
        self.connection.commit()
        return cursor

    def executemany(self, sql: str, rows: Iterable[Iterable[Any]]) -> None:
        self.connection.executemany(sql, rows)
        self.connection.commit()

    def one(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
        return self.connection.execute(sql, tuple(params)).fetchone()

    def all(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        return self.connection.execute(sql, tuple(params)).fetchall()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            self.connection.execute("BEGIN")
            yield self.connection
        except Exception:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()
