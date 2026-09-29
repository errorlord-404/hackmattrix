from typing import List

from bson.errors import InvalidId
from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, status

from app.models.farmer import Farmer
from app.schemas.farmer import FarmerCreate, FarmerResponse, FarmerUpdate

router = APIRouter(prefix="/farmers", tags=["farmers"])


def _to_response(farmer: Farmer) -> FarmerResponse:
    return FarmerResponse(
        id=str(farmer.id),
        name=farmer.name,
        phone=farmer.phone,
        location=farmer.location,
        preferred_language=farmer.preferred_language,
        field_ids=farmer.field_ids,
    )


def _to_object_id(farmer_id: str) -> PydanticObjectId:
    try:
        return PydanticObjectId(farmer_id)
    except (InvalidId, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid farmer ID")


@router.post("", response_model=FarmerResponse, status_code=status.HTTP_201_CREATED)
async def create_farmer(payload: FarmerCreate):
    farmer = Farmer(**payload.model_dump())
    await farmer.insert()
    return _to_response(farmer)


@router.get("", response_model=List[FarmerResponse])
async def list_farmers():
    farmers = await Farmer.find_all().to_list()
    return [_to_response(farmer) for farmer in farmers]


@router.get("/{farmer_id}", response_model=FarmerResponse)
async def get_farmer(farmer_id: str):
    farmer = await Farmer.get(_to_object_id(farmer_id))
    if not farmer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farmer not found")
    return _to_response(farmer)


@router.put("/{farmer_id}", response_model=FarmerResponse)
async def update_farmer(farmer_id: str, payload: FarmerUpdate):
    farmer = await Farmer.get(_to_object_id(farmer_id))
    if not farmer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farmer not found")

    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        setattr(farmer, field_name, value)
    await farmer.save()
    return _to_response(farmer)


@router.delete("/{farmer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_farmer(farmer_id: str):
    farmer = await Farmer.get(_to_object_id(farmer_id))
    if not farmer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farmer not found")
    await farmer.delete()
