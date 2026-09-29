from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def standalone_root() -> Path:
    configured = os.getenv("KISANSATHI_STANDALONE_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    source = Path(__file__).resolve()
    candidates = [source.parents[index] for index in range(min(5, len(source.parents)))]
    candidates.extend((Path.cwd(), Path.cwd().parent))
    for candidate in candidates:
        if (candidate / "models").is_dir() and (candidate / "docs").is_dir():
            return candidate
    return source.parents[2]


class Settings(BaseSettings):
    """Server-side API settings with paths rooted in the standalone bundle."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    mongodb_url: str = Field(default="mongodb://localhost:27017", validation_alias="MONGODB_URL")
    database_name: str = Field(default="kisansathi", validation_alias="DATABASE_NAME")
    mongodb_connect_timeout_ms: int = Field(default=2000, validation_alias="MONGODB_CONNECT_TIMEOUT_MS", ge=100, le=60000)
    farm_state_db_dir: Path = Field(default=Path("data/farm_state"), validation_alias="FARM_STATE_DB_DIR")
    farm_state_upload_dir: Path = Field(default=Path("data/farm_uploads"), validation_alias="FARM_STATE_UPLOAD_DIR")
    reference_db_enabled: bool = Field(default=False, validation_alias="REFERENCE_DB_ENABLED")
    default_tenant_id: str = Field(default="local", validation_alias="DEFAULT_TENANT_ID")
    default_farmer_id: str = Field(default="demo", validation_alias="DEFAULT_FARMER_ID")
    reference_page_size: int = Field(default=100, validation_alias="REFERENCE_PAGE_SIZE", ge=1, le=500)
    weather_provider: str = Field(default="open_meteo", validation_alias="WEATHER_PROVIDER")
    weather_timeout_seconds: float = Field(default=8.0, validation_alias="WEATHER_TIMEOUT_SECONDS", gt=0, le=60)
    weather_cache_seconds: int = Field(default=900, validation_alias="WEATHER_CACHE_SECONDS", ge=0, le=86400)
    max_diagnosis_image_bytes: int = Field(default=8 * 1024 * 1024, validation_alias="MAX_DIAGNOSIS_IMAGE_BYTES", ge=1)
    max_voice_audio_bytes: int = Field(default=10 * 1024 * 1024, validation_alias="MAX_VOICE_AUDIO_BYTES", ge=1)
    diagnosis_provider: str = Field(default="unconfigured", validation_alias="DIAGNOSIS_PROVIDER")
    sarvam_api_key: str = Field(default="", validation_alias="SARVAM_API_KEY", repr=False)
    sarvam_base_url: str = Field(default="https://api.sarvam.ai", validation_alias="SARVAM_BASE_URL")
    crop_model_dir: Path = Field(default=Path("models/crop_disease/downloaded"), validation_alias="CROP_MODEL_DIR")
    crop_model_registry_path: Path = Field(default=Path("models/crop_disease/registry.json"), validation_alias="CROP_MODEL_REGISTRY_PATH")
    crop_model_cache_size: int = Field(default=2, validation_alias="CROP_MODEL_CACHE_SIZE", ge=1, le=16)
    crop_model_device: str = Field(default="auto", validation_alias="CROP_MODEL_DEVICE")
    crop_disease_research_mode: bool = Field(default=False, validation_alias="CROP_DISEASE_RESEARCH_MODE")
    crop_disease_min_confidence: float = Field(default=0.60, validation_alias="CROP_DISEASE_MIN_CONFIDENCE", ge=0, le=1)
    crop_disease_max_pixels: int = Field(default=24_000_000, validation_alias="CROP_DISEASE_MAX_PIXELS", ge=1)
    cv_release_manifest_path: Path = Field(default=Path("models/manifests/approved-release.yaml"), validation_alias="CV_RELEASE_MANIFEST_PATH")
    cv_approval_record_path: Path = Field(default=Path("docs/APPROVED_RELEASES.json"), validation_alias="CV_APPROVAL_RECORD_PATH")
    cv_descriptor_signing_secret: str = Field(default="", validation_alias="CV_DESCRIPTOR_SIGNING_SECRET", repr=False)

    @property
    def runtime_db_dir(self) -> Path:
        return self._resolve(self.farm_state_db_dir)

    @property
    def runtime_upload_dir(self) -> Path:
        return self._resolve(self.farm_state_upload_dir)

    @property
    def runtime_crop_model_dir(self) -> Path:
        return self._resolve(self.crop_model_dir)

    @property
    def runtime_crop_model_registry_path(self) -> Path:
        return self._resolve(self.crop_model_registry_path)

    @property
    def runtime_cv_release_manifest_path(self) -> Path:
        return self._resolve(self.cv_release_manifest_path)

    @property
    def runtime_cv_approval_record_path(self) -> Path:
        return self._resolve(self.cv_approval_record_path)

    def _resolve(self, value: Path) -> Path:
        path = value.expanduser()
        return path if path.is_absolute() else standalone_root() / path

    def ensure_runtime_roots(self) -> tuple[Path, Path]:
        roots = (self.runtime_db_dir, self.runtime_upload_dir)
        for root in roots:
            root.mkdir(parents=True, exist_ok=True)
            probe = root / ".write-check"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        return roots


settings = Settings()
