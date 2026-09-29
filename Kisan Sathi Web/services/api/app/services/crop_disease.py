from __future__ import annotations

import sys
from pathlib import Path
from fastapi import Request
from app.core.config import settings as api_settings

ROOT = api_settings._resolve(Path("."))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.crop_disease.service import CropDiseaseInferenceService
from models.crop_disease.registry import CropDiseaseRegistry
from models.crop_disease.router import CropDiseaseRouter


def get_crop_disease_service(request: Request) -> CropDiseaseInferenceService:
    service = getattr(request.app.state, "crop_disease_service", None)
    if service is None:
        service_settings = getattr(request.app.state, "settings", None)
        environment = getattr(service_settings, "environment", "development")
        service = CropDiseaseInferenceService(
            CropDiseaseRouter(
                registry=CropDiseaseRegistry.from_path(api_settings.runtime_crop_model_registry_path),
                downloaded_root=api_settings.runtime_crop_model_dir,
                cache_size=api_settings.crop_model_cache_size,
                device=api_settings.crop_model_device,
                min_confidence=api_settings.crop_disease_min_confidence,
                allow_research_models=api_settings.crop_disease_research_mode or environment != "production",
            ),
            max_bytes=api_settings.max_diagnosis_image_bytes,
            max_pixels=api_settings.crop_disease_max_pixels,
        )
        request.app.state.crop_disease_service = service
    return service
