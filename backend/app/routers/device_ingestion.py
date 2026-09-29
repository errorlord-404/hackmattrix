"""Device-authenticated soil-node ingestion; this router never exposes a device secret."""

from __future__ import annotations

import hmac
import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.core.config import settings
from app.farm_state.dependencies import get_farm_store
from app.farm_state.store import FarmStateStore, iso_now
from app.schemas.device_ingestion import DeviceHealthResponse, DeviceTelemetryEnvelope, DeviceTelemetryResponse


router = APIRouter(prefix="/v1/device-ingestion", tags=["device-ingestion"])


def _credentials() -> dict:
    try:
        loaded = json.loads(settings.DEVICE_INGESTION_CREDENTIALS_JSON)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=503, detail={"code": "device_ingestion_misconfigured", "message": "Device credential configuration is invalid."}) from exc
    return loaded if isinstance(loaded, dict) else {}


def _authorize_device(device_id: str, authorization: str | None) -> dict:
    record = _credentials().get(device_id)
    if not isinstance(record, dict) or not isinstance(record.get("token"), str):
        raise HTTPException(status_code=401, detail={"code": "device_not_provisioned", "message": "Device is not provisioned."})
    token = authorization.removeprefix("Bearer ").strip() if authorization else ""
    if not token or not hmac.compare_digest(token, record["token"]):
        raise HTTPException(status_code=401, detail={"code": "device_auth_failed", "message": "Device authentication failed."})
    if not isinstance(record.get("farmer_id"), str):
        raise HTTPException(status_code=503, detail={"code": "device_ingestion_misconfigured", "message": "Device farmer scope is missing."})
    return record


def _as_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@router.post("/observations", response_model=DeviceTelemetryResponse, status_code=status.HTTP_201_CREATED)
def ingest_observations(
    payload: DeviceTelemetryEnvelope,
    authorization: str | None = Header(default=None),
):
    """Accept one authenticated, sequence-idempotent soil-node telemetry packet."""
    credential = _authorize_device(payload.device_id, authorization)
    allowed_fields = credential.get("field_ids")
    if isinstance(allowed_fields, list) and payload.field_id not in allowed_fields:
        raise HTTPException(status_code=403, detail={"code": "device_field_forbidden", "message": "Device is not provisioned for this field."})
    store = FarmStateStore(credential["farmer_id"])
    try:
        if not store.one("SELECT id FROM fields WHERE id = ? AND active = 1", (payload.field_id,)):
            raise HTTPException(status_code=404, detail="Field not found")
        existing = store.one(
            "SELECT * FROM device_telemetry_packets WHERE device_id = ? AND boot_id = ? AND sequence = ?",
            (payload.device_id, payload.boot_id, payload.sequence),
        )
        if existing:
            if existing["field_id"] != payload.field_id or existing["observed_at"] != payload.observed_at.isoformat():
                raise HTTPException(status_code=409, detail={"code": "device_sequence_conflict", "message": "Sequence was already used with a different packet."})
            sample_counts = store.one(
                "SELECT SUM(CASE WHEN quality_status = 'accepted' THEN 1 ELSE 0 END) AS accepted, COUNT(*) AS total FROM device_telemetry_samples WHERE packet_id = ?",
                (existing["id"],),
            )
            return DeviceTelemetryResponse(
                packet_id=existing["id"], status=existing["status"], accepted_sample_count=sample_counts["accepted"] or 0,
                rejected_sample_count=sample_counts["total"] - (sample_counts["accepted"] or 0), observed_at=_as_datetime(existing["observed_at"]),
                received_at=_as_datetime(existing["received_at"]), message="Duplicate packet replayed without creating new readings.",
            )
        packet_id, received_at = str(uuid4()), iso_now()
        store.execute(
            """INSERT INTO device_telemetry_packets(id, device_id, field_id, boot_id, sequence, observed_at, received_at, firmware_version, transport, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'accepted')""",
            (packet_id, payload.device_id, payload.field_id, payload.boot_id, payload.sequence, payload.observed_at.isoformat(), received_at,
             payload.firmware_version, json.dumps(payload.transport.model_dump(), separators=(",", ":"))),
        )
        store.execute(
            """INSERT INTO sensor_devices(id, field_id, name, device_type, unit, active, created_at)
            VALUES (?, ?, ?, 'soil_node', NULL, 1, ?) ON CONFLICT(id) DO UPDATE SET field_id = excluded.field_id, active = 1""",
            (payload.device_id, payload.field_id, payload.device_id, received_at),
        )
        accepted = rejected = 0
        for sample in payload.samples:
            reason = None if sample.crc_ok else "crc_failed"
            quality = "accepted" if reason is None else "rejected"
            store.execute(
                """INSERT INTO device_telemetry_samples(id, packet_id, probe_id, measurement, value, unit, modbus_address, crc_ok, quality_status, calibration_revision, rejection_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid4()), packet_id, sample.probe_id, sample.measurement, sample.value, sample.unit, sample.modbus_address,
                 int(sample.crc_ok), quality, sample.calibration_revision, reason),
            )
            if reason:
                rejected += 1
                continue
            accepted += 1
            store.execute(
                """INSERT INTO sensor_readings(id, field_id, device_id, measurement, value, unit, observed_at, source, fetched_at, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)""",
                (str(uuid4()), payload.field_id, payload.device_id, sample.measurement, sample.value, sample.unit,
                 payload.observed_at.isoformat(), f"device:{payload.device_id}:{sample.probe_id}", received_at),
            )
        packet_status = "accepted" if accepted else "rejected"
        packet_reason = None if accepted else "no_crc_valid_samples"
        store.execute("UPDATE device_telemetry_packets SET status = ?, rejection_reason = ? WHERE id = ?", (packet_status, packet_reason, packet_id))
        return DeviceTelemetryResponse(
            packet_id=packet_id, status=packet_status, accepted_sample_count=accepted, rejected_sample_count=rejected,
            observed_at=payload.observed_at, received_at=_as_datetime(received_at),
            message="Telemetry accepted." if accepted else "No valid sensor sample was accepted; raw packet evidence was retained.",
        )
    finally:
        store.close()


@router.get("/devices", response_model=list[DeviceHealthResponse])
def list_device_health(
    field_id: str | None = Query(default=None),
    store: FarmStateStore = Depends(get_farm_store),
):
    """Read device freshness for the farmer; no secret or actuator state is exposed."""
    clauses, values = [], []
    if field_id:
        clauses.append("p.field_id = ?"); values.append(field_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = store.all(
        f"""SELECT p.* FROM device_telemetry_packets p
        INNER JOIN (SELECT device_id, MAX(received_at) AS last_received FROM device_telemetry_packets GROUP BY device_id) latest
        ON latest.device_id = p.device_id AND latest.last_received = p.received_at {where}
        ORDER BY p.received_at DESC""",
        tuple(values),
    )
    now = datetime.now(timezone.utc)
    result = []
    for row in rows:
        age = max(0, int((now - _as_datetime(row["received_at"])).total_seconds()))
        state = "rejected" if row["status"] == "rejected" else "fresh" if age <= 30 * 60 else "stale"
        result.append(DeviceHealthResponse(
            device_id=row["device_id"], field_id=row["field_id"], last_observed_at=_as_datetime(row["observed_at"]),
            last_received_at=_as_datetime(row["received_at"]), firmware_version=row["firmware_version"], status=state,
            age_seconds=age, latest_packet_status=row["status"], rejection_reason=row["rejection_reason"],
        ))
    return result
