from abc import ABC, abstractmethod
from typing import List, Optional

from app.models.fertilizer import Fertilizer


def _normalize(value: str) -> str:
    return value.strip().lower()


class FertilizerMutator(ABC):
    @abstractmethod
    async def recommend_fertilizer(
        self,
        crop_name: str,
        fertilizer_type: Optional[str] = None,
        max_budget_per_bag: Optional[float] = None,
    ) -> List[Fertilizer]:
        raise NotImplementedError


class MongoFertilizerMutator(FertilizerMutator):
    async def recommend_fertilizer(
        self,
        crop_name: str,
        fertilizer_type: Optional[str] = None,
        max_budget_per_bag: Optional[float] = None,
    ) -> List[Fertilizer]:
        fertilizers = await Fertilizer.find_all().to_list()
        crop_name_normalized = _normalize(crop_name)
        fertilizer_type_normalized = (
            _normalize(fertilizer_type) if fertilizer_type else None
        )

        filtered = [
            fertilizer
            for fertilizer in fertilizers
            if any(
                _normalize(suitable_crop) == crop_name_normalized
                for suitable_crop in fertilizer.suitable_crops
            )
        ]

        if not filtered:
            filtered = fertilizers

        def score(fertilizer: Fertilizer) -> tuple[int, int, int, float, float, str]:
            crop_score = int(
                any(
                    _normalize(suitable_crop) == crop_name_normalized
                    for suitable_crop in fertilizer.suitable_crops
                )
            )
            type_score = int(
                fertilizer_type_normalized is not None
                and fertilizer_type_normalized == _normalize(fertilizer.type)
            )
            budget_score = int(
                max_budget_per_bag is not None
                and fertilizer.subsidized_mrp <= max_budget_per_bag
            )
            return (
                crop_score,
                type_score,
                budget_score,
                fertilizer.govt_subsidy_per_bag,
                -fertilizer.subsidized_mrp,
                fertilizer.name.lower(),
            )

        return sorted(filtered, key=score, reverse=True)


def get_fertilizer_mutator() -> FertilizerMutator:
    return MongoFertilizerMutator()
