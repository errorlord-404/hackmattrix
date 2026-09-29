from typing import List

from bson.errors import InvalidId
from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, status

from app.models.crop import Crop
from app.schemas.crop import CropCreate, CropResponse, CropUpdate

router = APIRouter(prefix="/crops", tags=["crops"])


def _to_response(crop: Crop) -> CropResponse:
    return CropResponse(
        id=str(crop.id),
        name=crop.name,
        season=crop.season,
        water_requirement=crop.water_requirement,
        soil_compatibility=crop.soil_compatibility,
        previous_crop_compatibility=crop.previous_crop_compatibility,
        avg_yield_per_acre=crop.avg_yield_per_acre,
        avg_price_per_quintal=crop.avg_price_per_quintal,
        source=crop.source,
        source_url=crop.source_url,
        source_record_id=crop.source_record_id,
        fetched_at=crop.fetched_at,
    )


def _to_object_id(crop_id: str) -> PydanticObjectId:
    try:
        return PydanticObjectId(crop_id)
    except (InvalidId, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid crop ID")


@router.post("", response_model=CropResponse, status_code=status.HTTP_201_CREATED)
async def create_crop(payload: CropCreate):
    crop = Crop(**payload.model_dump())
    await crop.insert()
    return _to_response(crop)


@router.get("", response_model=List[CropResponse])
async def list_crops():
    crops = await Crop.find_all().to_list()
    return [_to_response(crop) for crop in crops]


@router.get("/{crop_id}", response_model=CropResponse)
async def get_crop(crop_id: str):
    crop = await Crop.get(_to_object_id(crop_id))
    if not crop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop not found")
    return _to_response(crop)


@router.put("/{crop_id}", response_model=CropResponse)
async def update_crop(crop_id: str, payload: CropUpdate):
    crop = await Crop.get(_to_object_id(crop_id))
    if not crop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop not found")

    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        setattr(crop, field_name, value)
    await crop.save()
    return _to_response(crop)


@router.delete("/{crop_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_crop(crop_id: str):
    crop = await Crop.get(_to_object_id(crop_id))
    if not crop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop not found")
    await crop.delete()
