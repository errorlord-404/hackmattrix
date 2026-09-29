from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationInfo, field_validator

from app.services.field_geometry import validate_field_boundary


CANONICAL_CROP_STAGES = frozenset({
    "land_preparation", "seed_treatment", "sowing", "germination", "vegetative",
    "flowering", "fruiting", "grain_filling", "maturity", "harvest",
})


def canonical_crop_stage(value: str) -> str:
    """Convert common human wording to a stable stage key for rules and history."""
    stage = "_".join(value.strip().lower().replace("-", " ").replace("/", " ").split())
    aliases = {
        "land_preparation": "land_preparation", "land_prep": "land_preparation",
        "seed_treatment": "seed_treatment", "seed_treating": "seed_treatment",
        "sowing": "sowing", "planting": "sowing", "germination": "germination",
        "vegetative": "vegetative", "vegetation": "vegetative",
        "flowering": "flowering", "blooming": "flowering",
        "fruiting": "fruiting", "fruit_set": "fruiting",
        "grain_filling": "grain_filling", "grain_fill": "grain_filling",
        "maturity": "maturity", "mature": "maturity", "harvest": "harvest", "harvesting": "harvest",
    }
    canonical = aliases.get(stage)
    if canonical not in CANONICAL_CROP_STAGES:
        expected = ", ".join(sorted(CANONICAL_CROP_STAGES))
        raise ValueError(f"stage must be one of: {expected}")
    return canonical


class Provenance(BaseModel):
    source: str
    observed_at: datetime
    fetched_at: datetime
    freshness_seconds: int = Field(ge=0)
    confidence: float | None = Field(default=None, ge=0, le=1)


class Recommendation(BaseModel):
    what: str
    why: str
    when: str
    cost_estimate: str
    expected_benefit: str
    alternatives: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class NotificationPreferences(BaseModel):
    enabled: bool = True
    channels: list[Literal["in_app", "push", "sms"]] = Field(default_factory=lambda: ["in_app"])


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    location: str | None = Field(default=None, max_length=200)
    preferred_language: str = Field(default="en", min_length=2, max_length=20)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    notification_preferences: NotificationPreferences = Field(default_factory=NotificationPreferences)


class ProfileResponse(ProfileUpdate):
    farmer_id: str
    updated_at: datetime


class StorageStatusResponse(BaseModel):
    """Connection status for the two deliberately separate data stores."""

    farmer_id: str
    farm_state: Literal["available"] = "available"
    farm_state_store: Literal["server_local_sqlite"] = "server_local_sqlite"
    reference_database: Literal["available", "unavailable"]


class FieldBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    area_acres: float = Field(gt=0, le=100000)
    boundary_geojson: dict[str, Any]
    current_crop: str | None = Field(default=None, max_length=120)

    @field_validator("boundary_geojson")
    @classmethod
    def validate_boundary(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_field_boundary(value)


class FieldCreate(FieldBase):
    pass


class FieldPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    area_acres: float | None = Field(default=None, gt=0, le=100000)
    boundary_geojson: dict[str, Any] | None = None
    current_crop: str | None = Field(default=None, max_length=120)
    active: bool | None = None

    @field_validator("boundary_geojson")
    @classmethod
    def validate_boundary(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        return FieldBase.model_validate({"name": "field", "area_acres": 1, "boundary_geojson": value}).boundary_geojson


class FieldResponse(FieldBase):
    id: str
    centroid_lat: float | None = None
    centroid_lon: float | None = None
    status: str
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MapFieldResponse(BaseModel):
    id: str
    name: str
    area_acres: float
    boundary_geojson: dict[str, Any]
    centroid_lat: float | None = None
    centroid_lon: float | None = None
    current_crop: str | None = None
    current_stage: str | None = None
    latest_moisture_percent: float | None = None
    alert_count: int


class CropCycleCreate(BaseModel):
    crop_name: str = Field(min_length=1, max_length=120)
    planted_at: datetime
    expected_harvest_date: date | None = None
    initial_stage: str = Field(default="sowing", min_length=1, max_length=80)

    @field_validator("initial_stage")
    @classmethod
    def normalize_initial_stage(cls, value: str) -> str:
        return canonical_crop_stage(value)


class CropStageUpdate(BaseModel):
    stage: str = Field(min_length=1, max_length=80)
    occurred_at: datetime | None = None
    note: str | None = Field(default=None, max_length=500)

    @field_validator("stage")
    @classmethod
    def normalize_stage(cls, value: str) -> str:
        return canonical_crop_stage(value)


class CropStageEventResponse(BaseModel):
    id: str
    stage: str
    occurred_at: datetime
    note: str | None = None


class CropCycleResponse(BaseModel):
    id: str
    field_id: str
    crop_name: str
    planted_at: datetime
    expected_harvest_date: date | None = None
    current_stage: str
    status: str
    stage_events: list[CropStageEventResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class HarvestLotCreate(BaseModel):
    harvested_on: date
    quantity: float = Field(gt=0, le=1_000_000_000)
    unit: Literal["kg", "quintal", "tonne"]
    grade: str | None = Field(default=None, max_length=80)
    storage_note: str | None = Field(default=None, max_length=300)
    final_harvest: bool = False


class HarvestLotResponse(HarvestLotCreate):
    id: str
    field_id: str
    crop_cycle_id: str
    crop_name: str
    source: Literal["farmer_reported"] = "farmer_reported"
    created_at: datetime


class SoilTestCreate(BaseModel):
    observed_at: datetime
    ph: float | None = Field(default=None, ge=0, le=14)
    organic_carbon: float | None = None
    nitrogen: float | None = None
    phosphorus: float | None = None
    potassium: float | None = None
    ec: float | None = Field(default=None, ge=0)
    moisture_percent: float | None = Field(default=None, ge=0, le=100)
    source: str = Field(min_length=1, max_length=120)
    confidence: float | None = Field(default=None, ge=0, le=1)


class SoilTestResponse(SoilTestCreate):
    id: str
    field_id: str
    fetched_at: datetime


class SensorReadingCreate(BaseModel):
    field_id: str
    device_id: str | None = None
    measurement: Literal["moisture", "temperature", "humidity", "ph", "ec", "nitrogen", "phosphorus", "potassium"]
    value: float
    unit: str = Field(min_length=1, max_length=30)
    observed_at: datetime
    source: str = Field(min_length=1, max_length=120)
    confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("unit")
    @classmethod
    def normalise_measurement_unit(cls, value: str, info: ValidationInfo) -> str:
        """Store only units the current screening rules can interpret safely."""
        measurement = info.data.get("measurement")
        compact = value.strip().lower().replace(" ", "")
        aliases = {
            "moisture": {"%": "%", "percent": "%", "percentage": "%"},
            "humidity": {"%": "%", "percent": "%", "percentage": "%"},
            "temperature": {"c": "°C", "°c": "°C", "celsius": "°C"},
            "ph": {"ph": "pH"},
            "ec": {"ms/cm": "mS/cm", "mscm-1": "mS/cm", "mscm^-1": "mS/cm"},
            "nitrogen": {"mg/kg": "mg/kg", "mgkg-1": "mg/kg", "mgkg^-1": "mg/kg"},
            "phosphorus": {"mg/kg": "mg/kg", "mgkg-1": "mg/kg", "mgkg^-1": "mg/kg"},
            "potassium": {"mg/kg": "mg/kg", "mgkg-1": "mg/kg", "mgkg^-1": "mg/kg"},
        }
        canonical = aliases.get(measurement, {}).get(compact)
        if not canonical:
            expected = {"moisture": "%", "humidity": "%", "temperature": "°C", "ph": "pH", "ec": "mS/cm"}.get(
                measurement, "mg/kg"
            )
            raise ValueError(f"unit for {measurement} must be compatible with {expected}")
        return canonical


class ObservationResponse(BaseModel):
    id: str
    field_id: str
    measurement: str
    value: float
    unit: str
    observed_at: datetime
    fetched_at: datetime
    source: str
    confidence: float | None = None


class TomatoDemoStart(BaseModel):
    scenario: Literal["balanced", "water-stress", "nitrogen-low", "salinity-risk", "alkaline-soil"] = "balanced"
    seed: int = Field(default=42, ge=0, le=2_147_483_647)


class TomatoDemoWeatherFixture(BaseModel):
    """Explicit local forecast fixture used only for a repeatable presentation."""

    scenario: Literal["ordinary-rain", "heavy-rain", "clear"]


class TomatoDemoResponse(BaseModel):
    enabled: bool
    field_id: str
    running: bool
    scenario: str | None = None
    seed: int | None = None
    tick_count: int = 0
    irrigation_ticks_remaining: int = 0
    observed_at: datetime | None = None
    updated_at: datetime | None = None
    source: str
    forecast_fixture: Literal["ordinary-rain", "heavy-rain"] | None = None
    observations: list[ObservationResponse] = Field(default_factory=list)


class SoilHealthResponse(BaseModel):
    field_id: str
    latest_test: SoilTestResponse | None = None
    latest_observations: list[ObservationResponse] = Field(default_factory=list)
    status: str
    recommendations: list[Recommendation] = Field(default_factory=list)
    provenance: list[Provenance] = Field(default_factory=list)


class WeatherData(BaseModel):
    provider: str
    latitude: float
    longitude: float
    observed_at: datetime
    fetched_at: datetime
    freshness_seconds: int
    current: dict[str, Any] = Field(default_factory=dict)
    hourly: list[dict[str, Any]] = Field(default_factory=list)
    daily: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class WeatherAlertResponse(BaseModel):
    id: str
    field_id: str | None = None
    alert_type: str
    title: str
    description: str
    severity: str
    provenance: Provenance


class IrrigationPlanResponse(BaseModel):
    id: str
    field_id: str
    status: str
    recommended_window_start: datetime | None = None
    recommended_window_end: datetime | None = None
    target_moisture_percent: float
    lower_moisture_percent: float | None = None
    upper_moisture_percent: float | None = None
    catalog_crop: str | None = None
    catalog_stage: str | None = None
    decision_mode: str = "weather_aware"
    estimated_volume_liters: float | None = None
    estimated_duration_minutes: float | None = None
    application_adjustment_percent: int | None = Field(default=None, ge=0, le=100)
    recommendation: Recommendation
    assumptions: list[str] = Field(default_factory=list)
    created_at: datetime


class IrrigationEventCreate(BaseModel):
    field_id: str
    occurred_at: datetime
    volume_liters: float | None = Field(default=None, ge=0)
    duration_minutes: float | None = Field(default=None, ge=0)
    method: str | None = None
    note: str | None = None


class IrrigationEventResponse(IrrigationEventCreate):
    id: str
    source: str


class CropOptionResponse(BaseModel):
    crop_name: str
    season: str | None = None
    reference_price_per_quintal: float | None = None
    price_source: str | None = None
    source_url: str | None = None
    checks: dict[str, bool | None]
    missing_evidence: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    status: Literal["candidate_needs_review", "not_recommended_with_current_inputs"]


class ReminderCreate(BaseModel):
    field_id: str | None = None
    reminder_type: str = Field(min_length=1, max_length=80)
    scheduled_for: datetime
    title: str = Field(min_length=1, max_length=200)


class ReminderResponse(ReminderCreate):
    id: str
    status: str
    created_at: datetime


class FieldTaskCreate(BaseModel):
    field_id: str
    title: str = Field(min_length=1, max_length=200)
    due_at: datetime | None = None
    source: str = Field(default="farmer_confirmed", min_length=1, max_length=120)


class FieldTaskPatch(BaseModel):
    status: Literal["open", "completed", "cancelled"]


class FieldTaskResponse(FieldTaskCreate):
    id: str
    status: Literal["open", "completed", "cancelled"]
    created_at: datetime


class CropStageActionProposalResponse(BaseModel):
    field_id: str
    crop_cycle_id: str
    crop_name: str
    stage: str
    title: str
    why: str
    due_hint: str
    source: str
    requires_farmer_confirmation: Literal[True] = True


class LedgerEntryCreate(BaseModel):
    """A farmer-entered INR ledger record, never a payment or credit instruction."""

    field_id: str | None = None
    entry_type: Literal["income", "expense"]
    category: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    amount_inr: float = Field(gt=0, le=1_000_000_000)
    occurred_at: date
    crop_name: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=1000)
    source: str = Field(default="farmer_confirmed", min_length=1, max_length=120)


class LedgerEntryPatch(BaseModel):
    status: Literal["active", "void"]


class LedgerEntryResponse(LedgerEntryCreate):
    id: str
    status: Literal["active", "void"]
    created_at: datetime
    voided_at: datetime | None = None


class LedgerSummaryResponse(BaseModel):
    currency: Literal["INR"] = "INR"
    income_inr: float = 0
    expense_inr: float = 0
    balance_inr: float = 0
    active_entry_count: int = 0
    assumptions: list[str] = Field(default_factory=lambda: [
        "Totals include only active farmer-entered INR ledger records.",
        "This is a record-keeping summary, not a financial forecast, tax statement, or credit decision.",
    ])


class AlertResponse(BaseModel):
    id: str
    field_id: str | None = None
    kind: str
    title: str
    message: str
    severity: str
    status: str
    source: str
    created_at: datetime
    updated_at: datetime


class AlertPatch(BaseModel):
    status: Literal["open", "read", "dismissed"]


class DashboardResponse(BaseModel):
    generated_at: datetime
    fields: list[MapFieldResponse] = Field(default_factory=list)
    weather: WeatherData | None = None
    market_summary: list[dict[str, Any]] = Field(default_factory=list)
    alerts: list[AlertResponse] = Field(default_factory=list)
    data_warnings: list[str] = Field(default_factory=list)


class DiagnosisResponse(BaseModel):
    id: str
    field_id: str | None = None
    status: Literal["queued", "inconclusive", "completed", "failed", "provider_unavailable", "needs_crop_confirmation", "unsupported_crop", "needs_expert_review"]
    label: str | None = None
    confidence: float | None = None
    severity: str | None = None
    treatment: str | None = None
    provider: str | None = None
    error: str | None = None
    crop: str | None = None
    model_id: str | None = None
    model_version: str | None = None
    inference_location: str | None = None
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    crop_candidates: list[dict[str, Any]] = Field(default_factory=list)
    model_evidence: list[dict[str, Any]] = Field(default_factory=list)
    context_snapshot: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, list[Any]] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    created_at: datetime


class MediaUploadResponse(BaseModel):
    upload_id: str
    field_id: str | None = None
    mime_type: str
    size_bytes: int
    checksum: str
    status: Literal["stored_private"]
    created_at: datetime
    expires_at: datetime


class MediaConsentCreate(BaseModel):
    provider: Literal["kindwise_crop_health"]
    purpose: Literal["crop_health_assessment"] = "crop_health_assessment"
    notice_version: str = Field(default="crop-health-v1", min_length=1, max_length=80)
    decision: Literal["approved", "declined"]


class MediaConsentResponse(BaseModel):
    consent_receipt_id: str
    upload_id: str
    provider: str
    purpose: str
    decision: Literal["approved", "declined"]
    created_at: datetime
    expires_at: datetime


class DiagnosisFromUploadCreate(BaseModel):
    upload_id: str = Field(min_length=1, max_length=120)
    consent_receipt_id: str = Field(min_length=1, max_length=120)
    confirmed_crop: str | None = Field(default=None, max_length=120)


class DiagnosisFeedbackCreate(BaseModel):
    """Farmer feedback is a review lead, not a training-label approval."""

    correctness: Literal["confirmed", "corrected", "unknown"]
    confirmed_crop: str | None = Field(default=None, min_length=1, max_length=120)
    label: str | None = Field(default=None, min_length=1, max_length=120)
    share_for_model_improvement: bool = False
    note: str | None = Field(default=None, max_length=500)

    @field_validator("label")
    @classmethod
    def normalise_label(cls, value: str | None) -> str | None:
        return value.strip() if value else None

    @field_validator("confirmed_crop")
    @classmethod
    def normalise_crop(cls, value: str | None) -> str | None:
        return value.strip() if value else None

    def model_post_init(self, __context: Any) -> None:
        if self.correctness in {"confirmed", "corrected"} and not self.label:
            raise ValueError("label is required when correctness is confirmed or corrected")


class DiagnosisFeedbackResponse(BaseModel):
    id: str
    diagnosis_id: str
    confirmed_crop: str | None = None
    label: str | None = None
    correctness: Literal["confirmed", "corrected", "unknown"]
    share_for_model_improvement: bool
    note: str | None = None
    reviewer_type: Literal["farmer"] = "farmer"
    training_eligibility: Literal["requires_expert_review_and_separate_export"] = "requires_expert_review_and_separate_export"
    created_at: datetime


class AdvisorSessionCreate(BaseModel):
    field_id: str | None = None
    language: str = Field(default="en", min_length=2, max_length=20)


class AdvisorSessionResponse(BaseModel):
    id: str
    field_id: str | None = None
    language: str
    status: str
    created_at: datetime
    updated_at: datetime


class AdvisorMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    idempotency_key: str | None = Field(default=None, max_length=120)


class AdvisorMessageResponse(BaseModel):
    id: str
    session_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    provider: str | None = None
    created_at: datetime


class VoiceTurnResponse(BaseModel):
    status: Literal["provider_unavailable", "completed", "inconclusive"]
    transcript: str | None = None
    response_text: str | None = None
    language: str | None = None
    audio_base64: str | None = None
    audio_mime_type: str | None = None
    provider: str | None = None
    message: str


class VoiceTranscriptionResponse(BaseModel):
    status: Literal["completed", "provider_unavailable", "inconclusive"]
    transcript: str | None = None
    language_code: str | None = None
    provider: str | None = None
    request_id: str | None = None
    message: str


class VoiceSynthesisRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2500)
    language_code: str = Field(min_length=2, max_length=20)
    speaker: str | None = Field(default=None, min_length=1, max_length=40)
    model: str | None = Field(default=None, min_length=1, max_length=40)
    pace: float | None = Field(default=None, ge=0.5, le=2.0)
    speech_sample_rate: int | None = Field(default=None, ge=8000, le=48000)
    output_audio_codec: str | None = Field(default=None, min_length=3, max_length=20)


class VoiceSynthesisResponse(BaseModel):
    status: Literal["completed", "provider_unavailable", "inconclusive"]
    audio_base64: str | None = None
    audio_mime_type: str | None = None
    language_code: str | None = None
    provider: str | None = None
    request_id: str | None = None
    message: str


class TranslationRequest(BaseModel):
    input: str = Field(min_length=1, max_length=2000)
    source_language_code: str = Field(min_length=2, max_length=20)
    target_language_code: str = Field(min_length=2, max_length=20)
    model: str | None = Field(default=None, min_length=1, max_length=40)
    mode: str | None = Field(default=None, min_length=1, max_length=40)
    output_script: str | None = Field(default=None, min_length=1, max_length=40)


class TranslationResponse(BaseModel):
    status: Literal["completed", "provider_unavailable", "inconclusive"]
    translated_text: str | None = None
    source_language_code: str | None = None
    target_language_code: str | None = None
    provider: str | None = None
    request_id: str | None = None
    message: str


class SarvamRuntimeConfigUpdate(BaseModel):
    """Local-session configuration. The API key is never included in a response."""

    api_key: SecretStr | None = None
    clear_api_key: bool = False
    stt_model: str | None = Field(default=None, min_length=1, max_length=80)
    stt_language_code: str | None = Field(default=None, min_length=2, max_length=20)
    tts_model: str | None = Field(default=None, min_length=1, max_length=80)
    tts_speaker: str | None = Field(default=None, min_length=1, max_length=80)
    tts_pace: float | None = Field(default=None, ge=0.5, le=2.0)
    translate_model: str | None = Field(default=None, min_length=1, max_length=80)


class SarvamRuntimeConfigResponse(BaseModel):
    configured: bool
    voice_provider: str
    api_key_storage: str = "active backend process only"
    stt_model: str
    stt_language_code: str
    tts_model: str
    tts_speaker: str
    tts_pace: float
    translate_model: str


class ReportCreate(BaseModel):
    report_type: Literal["farm_summary", "crop_health", "water", "market"] = "farm_summary"
    from_date: date | None = None
    to_date: date | None = None


class ReportResponse(BaseModel):
    id: str
    report_type: str
    from_date: date | None = None
    to_date: date | None = None
    status: Literal["queued", "completed", "failed"]
    input_snapshot: dict[str, Any]
    artifact: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

