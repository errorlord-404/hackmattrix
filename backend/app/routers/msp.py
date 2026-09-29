from typing import List

from bson.errors import InvalidId
from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Query, status

from app.models.market_price import MarketPrice
from app.models.msp import MSP
from app.schemas.msp import MSPCreate, MSPMarketComparisonResponse, MSPResponse, MSPUpdate
from app.services.msp_comparison import select_msp_market_comparison

router = APIRouter(prefix="/msp", tags=["msp"])


def _to_response(msp: MSP) -> MSPResponse:
    return MSPResponse(
        id=str(msp.id),
        crop_name=msp.crop_name,
        msp_price_per_quintal=msp.msp_price_per_quintal,
        season=msp.season,
        marketing_year=msp.marketing_year,
        procurement_centres=msp.procurement_centres,
        variety=msp.variety,
        source=msp.source,
        source_url=msp.source_url,
        source_record_id=msp.source_record_id,
        fetched_at=msp.fetched_at,
    )


def _to_object_id(msp_id: str) -> PydanticObjectId:
    try:
        return PydanticObjectId(msp_id)
    except (InvalidId, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid MSP ID")


@router.post("", response_model=MSPResponse, status_code=status.HTTP_201_CREATED)
async def create_msp(payload: MSPCreate):
    msp = MSP(**payload.model_dump())
    await msp.insert()
    return _to_response(msp)


@router.get("", response_model=List[MSPResponse])
async def list_msps():
    msps = await MSP.find_all().to_list()
    return [_to_response(msp) for msp in msps]


@router.get("/by-crop/{crop_name}", response_model=List[MSPResponse])
async def list_msps_by_crop(crop_name: str):
    msps = await MSP.find(MSP.crop_name == crop_name).to_list()
    return [_to_response(msp) for msp in msps]


@router.get("/compare-market", response_model=MSPMarketComparisonResponse)
async def compare_msp_with_market(crop: str = Query(..., min_length=1)):
    """Compare sourced MSP and newest observation per mandi; no procurement promise."""
    return select_msp_market_comparison(crop, await MSP.find_all().to_list(), await MarketPrice.find_all().to_list())


@router.get("/{msp_id}", response_model=MSPResponse)
async def get_msp(msp_id: str):
    msp = await MSP.get(_to_object_id(msp_id))
    if not msp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MSP not found")
    return _to_response(msp)


@router.put("/{msp_id}", response_model=MSPResponse)
async def update_msp(msp_id: str, payload: MSPUpdate):
    msp = await MSP.get(_to_object_id(msp_id))
    if not msp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MSP not found")

    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        setattr(msp, field_name, value)
    await msp.save()
    return _to_response(msp)


@router.delete("/{msp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_msp(msp_id: str):
    msp = await MSP.get(_to_object_id(msp_id))
    if not msp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MSP not found")
    await msp.delete()
