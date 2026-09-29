from pathlib import Path

from PIL import Image

from models.crop_disease.adapters.base import DiseaseModelAdapter, RawPrediction
from models.crop_disease.ontology import normalize_crop
from models.crop_disease.registry import CropDiseaseRegistry, default_registry_path
from models.crop_disease.router import CropDiseaseRouter


class FakeAdapter(DiseaseModelAdapter):
    def load(self): pass
    def predict(self, image, top_k=3): return [RawPrediction("Tomato___healthy", 0.92)]


def ready_router(tmp_path: Path) -> CropDiseaseRouter:
    registry = CropDiseaseRegistry.from_path(default_registry_path())
    entry = registry.get("mesabo_resnet50")
    path = tmp_path / entry.local_path
    path.mkdir(parents=True)
    (path / "download-manifest.json").write_text("{}", encoding="utf-8")
    return CropDiseaseRouter(registry=registry, downloaded_root=tmp_path, adapter_factory=lambda *_: FakeAdapter())


def test_aliases_cover_indian_names():
    assert normalize_crop("bajra") == "pearl_millet"
    assert normalize_crop("corn") == "maize"
    assert normalize_crop("unknown crop") is None


def test_tomato_routes_to_local_specialist(tmp_path: Path):
    result = ready_router(tmp_path).predict(Image.new("RGB", (8, 8)), crop="tomato")
    assert result.status == "healthy"
    assert result.model and result.model.id == "mesabo_resnet50"
    assert result.prediction and result.prediction.disease_id == "tomato_healthy"


def test_unqualified_crop_returns_safe_unavailable(tmp_path: Path):
    result = ready_router(tmp_path).predict(Image.new("RGB", (8, 8)), crop="rice")
    assert result.status == "model_unavailable"
    assert result.model_available is False


def test_ensemble_is_never_silently_enabled(tmp_path: Path):
    result = ready_router(tmp_path).predict(Image.new("RGB", (8, 8)), crop="tomato", mode="ensemble")
    assert result.status == "ensemble_unavailable"


def test_production_router_blocks_research_models(tmp_path: Path):
    router = ready_router(tmp_path)
    router.allow_research_models = False
    result = router.predict(Image.new("RGB", (8, 8)), crop="tomato")
    assert result.status == "model_unavailable"
    assert result.routing.reason == "production_release_required"
