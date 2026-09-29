"""Dedicated gateway telemetry contract; intentionally separate from agent writes."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from app.schemas.farm_state import SensorReadingCreate


class DeviceTransport(BaseModel):
    rssi_dbm: int | None = Field(default=None, ge=-160, le=0)
    queued_seconds: int = Field(default=0, ge=0, le=7 * 24 * 60 * 60)


class DeviceTelemetrySample(BaseModel):
    probe_id: str = Field(min_length=1, max_length=120)
    measurement: Literal["moisture", "temperature", "humidity", "ph", "ec", "nitrogen", "phosphorus", "potassium"]
    value: float
    unit: str = Field(min_length=1, max_length=30)
    modbus_address: int = Field(ge=1, le=247)
    crc_ok: bool
    calibration_revision: str | None = Field(default=None, max_length=120)

    @field_validator("unit")
    @classmethod
    def normalize_unit(cls, value: str, info: ValidationInfo) -> str:
        # Reuse the farmer-reading unit contract so telemetry cannot introduce
        # a second set of agronomic unit meanings.
        return SensorReadingCreate.model_validate({
            "field_id": "device-contract", "measurement": info.data.get("measurement"), "value": 0,
            "unit": value, "observed_at": "2026-01-01T00:00:00Z", "source": "device:contract",
        }).unit


class DeviceTelemetryEnvelope(BaseModel):
    device_id: str = Field(min_length=3, max_length=120, pattern=r"^[A-Za-z0-9._:-]+$")
    field_id: str = Field(min_length=1, max_length=120)
    boot_id: str = Field(min_length=3, max_length=120, pattern=r"^[A-Za-z0-9._:-]+$")
    sequence: int = Field(ge=0)
    observed_at: datetime
    firmware_version: str = Field(min_length=1, max_length=80)
    samples: list[DeviceTelemetrySample] = Field(min_length=1, max_length=24)
    transport: DeviceTransport = Field(default_factory=DeviceTransport)


class DeviceTelemetryResponse(BaseModel):
    packet_id: str
    status: Literal["accepted", "rejected"]
    accepted_sample_count: int
    rejected_sample_count: int
    observed_at: datetime
    received_at: datetime
    message: str


class DeviceHealthResponse(BaseModel):
    device_id: str
    field_id: str
    last_observed_at: datetime
    last_received_at: datetime
    firmware_version: str
    status: Literal["fresh", "stale", "rejected"]
    age_seconds: int
    latest_packet_status: Literal["accepted", "rejected"]
    rejection_reason: str | None = None
