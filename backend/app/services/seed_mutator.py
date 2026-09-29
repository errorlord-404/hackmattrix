from abc import ABC, abstractmethod
from typing import List, Optional

from app.models.seed import Seed


def _normalize(value: str) -> str:
    return value.strip().lower()


class SeedMutator(ABC):
    @abstractmethod
    async def recommend_seed(
        self,
        crop: str,
        preferred_zone: Optional[str] = None,
        disease_risk: Optional[str] = None,
    ) -> List[Seed]:
        raise NotImplementedError


class MongoSeedMutator(SeedMutator):
    async def recommend_seed(
        self,
        crop: str,
        preferred_zone: Optional[str] = None,
        disease_risk: Optional[str] = None,
    ) -> List[Seed]:
        seeds = await Seed.find(Seed.crop == crop).to_list()
        crop_normalized = _normalize(crop)

        if not seeds:
            seeds = await Seed.find_all().to_list()

        zone_normalized = _normalize(preferred_zone) if preferred_zone else None
        disease_risk_normalized = _normalize(disease_risk) if disease_risk else None

        def score(seed: Seed) -> tuple[int, int, int, str]:
            crop_score = int(_normalize(seed.crop) == crop_normalized)
            zone_score = int(
                zone_normalized is not None
                and zone_normalized in _normalize(seed.recommended_zone)
            )
            disease_score = int(
                disease_risk_normalized is not None
                and disease_risk_normalized in _normalize(seed.disease_resistance)
            )
            return (
                crop_score,
                zone_score,
                disease_score,
                seed.variety.lower(),
            )

        return sorted(seeds, key=score, reverse=True)


def get_seed_mutator() -> SeedMutator:
    return MongoSeedMutator()
