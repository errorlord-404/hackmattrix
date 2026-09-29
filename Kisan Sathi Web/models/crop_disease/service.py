from __future__ import annotations

from io import BytesIO
from PIL import Image, ImageOps, UnidentifiedImageError

from .router import CropDiseaseRouter
from .schemas import DiseaseInferenceResult


class CropDiseaseInferenceService:
    def __init__(self, router: CropDiseaseRouter | None = None, *, max_bytes: int = 8 * 1024 * 1024, max_pixels: int = 24_000_000) -> None:
        self.router, self.max_bytes, self.max_pixels = router or CropDiseaseRouter(), max_bytes, max_pixels

    def predict(self, content: bytes, **request: object) -> DiseaseInferenceResult:
        if not content or len(content) > self.max_bytes:
            raise ValueError("image is empty or exceeds the configured byte limit")
        try:
            with Image.open(BytesIO(content)) as source:
                if source.width * source.height > self.max_pixels:
                    raise ValueError("image exceeds the configured pixel limit")
                image = ImageOps.exif_transpose(source).convert("RGB").copy()
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError("upload is not a readable image") from exc
        return self.router.predict(image, **request)
