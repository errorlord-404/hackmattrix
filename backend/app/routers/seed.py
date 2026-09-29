from typing import List

from bson.errors import InvalidId
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.models.seed import Seed
from app.schemas.seed import (
    SeedCreate,
    SeedRecommendationRequest,
    SeedRecommendationResponse,
    SeedResponse,
    SeedUpdate,
)
from app.services.seed_mutator import SeedMutator, get_seed_mutator

router = APIRouter(prefix="/seeds", tags=["seeds"])


def _to_response(seed: Seed) -> SeedResponse:
    return SeedResponse(
        id=str(seed.id),
        crop=seed.crop,
        variety=seed.variety,
        duration_days=seed.duration_days,
        yield_potential=seed.yield_potential,
        disease_resistance=seed.disease_resistance,
        recommended_zone=seed.recommended_zone,
    )


def _to_object_id(seed_id: str) -> PydanticObjectId:
    try:
        return PydanticObjectId(seed_id)
    except (InvalidId, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid seed ID")


@router.post("", response_model=SeedResponse, status_code=status.HTTP_201_CREATED)
async def create_seed(payload: SeedCreate):
    seed = Seed(**payload.model_dump())
    await seed.insert()
    return _to_response(seed)


@router.get("", response_model=List[SeedResponse])
async def list_seeds():
    seeds = await Seed.find_all().to_list()
    return [_to_response(seed) for seed in seeds]


@router.post("/recommend", response_model=SeedRecommendationResponse)
async def recommend_seed(
    payload: SeedRecommendationRequest,
    mutator: SeedMutator = Depends(get_seed_mutator),
):
    seeds = await mutator.recommend_seed(
        crop=payload.crop,
        preferred_zone=payload.preferred_zone,
        disease_risk=payload.disease_risk,
    )
    return SeedRecommendationResponse(
        crop=payload.crop,
        preferred_zone=payload.preferred_zone,
        disease_risk=payload.disease_risk,
        recommended_seeds=[_to_response(seed) for seed in seeds],
    )


@router.get("/{seed_id}", response_model=SeedResponse)
async def get_seed(seed_id: str):
    seed = await Seed.get(_to_object_id(seed_id))
    if not seed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seed not found")
    return _to_response(seed)


@router.put("/{seed_id}", response_model=SeedResponse)
async def update_seed(seed_id: str, payload: SeedUpdate):
    seed = await Seed.get(_to_object_id(seed_id))
    if not seed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seed not found")

    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        setattr(seed, field_name, value)
    await seed.save()
    return _to_response(seed)


@router.delete("/{seed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_seed(seed_id: str):
    seed = await Seed.get(_to_object_id(seed_id))
    if not seed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seed not found")
    await seed.delete()
