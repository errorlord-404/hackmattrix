"""Canonical crop aliases and lossless PlantVillage-style label normalization."""

from __future__ import annotations

import re
from dataclasses import dataclass


CANONICAL_CROPS = (
    "rice", "wheat", "maize", "sorghum", "pearl_millet", "finger_millet",
    "chickpea", "pigeon_pea", "mung_bean", "black_gram", "groundnut", "soybean",
    "rapeseed_mustard", "cotton", "jute", "sugarcane", "potato", "tomato", "onion",
    "chilli", "banana", "mango", "citrus", "grape", "tea", "coconut",
)

_ALIASES = {
    "corn": "maize", "maize": "maize", "pearl millet": "pearl_millet", "bajra": "pearl_millet",
    "finger millet": "finger_millet", "ragi": "finger_millet", "mustard": "rapeseed_mustard",
    "rapeseed": "rapeseed_mustard", "pigeon pea": "pigeon_pea", "tur": "pigeon_pea",
    "arhar": "pigeon_pea", "mung": "mung_bean", "moong": "mung_bean", "mung bean": "mung_bean",
    "black gram": "black_gram", "urad": "black_gram", "peanut": "groundnut",
    "chili": "chilli", "hot pepper": "chilli", "orange": "citrus",
}

_CROP_PREFIXES = {
    "corn": "maize", "maize": "maize", "potato": "potato", "tomato": "tomato",
    "orange": "citrus", "citrus": "citrus", "grape": "grape", "soybean": "soybean",
    "pepper": "chilli", "bell pepper": "chilli",
}


def normalize_crop(value: str | None) -> str | None:
    if value is None:
        return None
    compact = re.sub(r"[\s_-]+", " ", value.strip().casefold())
    if not compact:
        return None
    candidate = _ALIASES.get(compact, compact.replace(" ", "_"))
    return candidate if candidate in CANONICAL_CROPS else None


def display_name(identifier: str) -> str:
    return identifier.replace("_", " ").title()


@dataclass(frozen=True, slots=True)
class CanonicalLabel:
    disease_id: str
    disease_name: str
    raw_model_label: str
    healthy: bool


def normalize_disease_label(raw_label: str, requested_crop: str) -> CanonicalLabel:
    """Normalize known label forms while retaining the original raw label."""

    text = raw_label.strip()
    compact = re.sub(r"___|[\s/_-]+", " ", text.casefold()).strip()
    crop = requested_crop
    for prefix, canonical_crop in _CROP_PREFIXES.items():
        if compact.startswith(prefix + " ") or compact == prefix:
            crop = canonical_crop
            compact = compact[len(prefix):].strip()
            break
    disease = re.sub(r"[^a-z0-9]+", "_", compact).strip("_") or "unmapped"
    healthy = disease in {"healthy", "health"}
    if healthy:
        disease = "healthy"
    if crop == "citrus" and disease in {"huanglongbing", "citrus_greening", "greening"}:
        disease = "huanglongbing"
    return CanonicalLabel(
        disease_id=f"{crop}_{disease}",
        disease_name="Healthy" if healthy else display_name(disease),
        raw_model_label=text,
        healthy=healthy,
    )

