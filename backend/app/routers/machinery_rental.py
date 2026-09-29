from beanie import PydanticObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query, status

from app.models.machinery_rental import MachineryRental
from app.schemas.machinery_rental import (
    MachineryRentalCreate,
    MachineryRentalResponse,
    MachineryRentalUpdate,
)
from app.services.geo import haversine_km, normalize_admin

router = APIRouter(prefix="/machinery-rentals", tags=["machinery-rentals"])


def _to_response(item: MachineryRental) -> MachineryRentalResponse:
    payload = item.model_dump(exclude={"id"})
    # Older live FARMS rows may predate the explicit parser fallback and have
    # no address. Keep the source row queryable without inventing a location.
    if not (payload.get("location") or payload.get("village")):
        payload["location"] = payload.get("district") or payload.get("state") or "Location not provided by source"
    return MachineryRentalResponse(id=str(item.id), **payload)


def _normalise_aliases(values: dict, *, fill_defaults: bool = False) -> dict:
    if "provider_name" in values or "owner_name" in values:
        provider = values.get("provider_name") or values.get("owner_name")
        values["provider_name"] = provider
        values["owner_name"] = values.get("owner_name") or provider
    if "location" in values or "village" in values:
        location = values.get("location") or values.get("village")
        values["location"] = location
        values["village"] = values.get("village") or location
    if "contact_phone" in values or "phone" in values:
        phone = values.get("contact_phone") or values.get("phone")
        values["contact_phone"] = phone
        values["phone"] = values.get("phone") or phone
    if fill_defaults or "availability_status" in values or "available_status" in values:
        availability = values.get("available_status") or values.get("availability_status") or "unknown"
        values["availability_status"] = availability
        values["available_status"] = values.get("available_status") or availability
    return values


def _to_object_id(rental_id: str) -> PydanticObjectId:
    try:
        return PydanticObjectId(rental_id)
    except (InvalidId, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid machinery rental ID",
        ) from exc


@router.post("", response_model=MachineryRentalResponse, status_code=status.HTTP_201_CREATED)
async def create_machinery_rental(payload: MachineryRentalCreate):
    rental = MachineryRental(**_normalise_aliases(payload.model_dump(), fill_defaults=True))
    await rental.insert()
    return _to_response(rental)


@router.get("", response_model=list[MachineryRentalResponse])
async def list_machinery_rentals(
    category: str | None = Query(default=None, min_length=1),
    district: str | None = Query(default=None, min_length=1),
    state: str | None = Query(default=None, min_length=1),
):
    criteria: dict[str, str] = {}
    if category:
        criteria["category"] = category
    if district:
        criteria["district"] = normalize_admin(district)
    if state:
        criteria["state"] = normalize_admin(state)
    records = await (MachineryRental.find(criteria) if criteria else MachineryRental.find_all()).to_list()
    records.sort(key=lambda item: (item.record_kind != "provider_listing", item.distance_km if item.distance_km is not None else float("inf")))
    return [_to_response(record) for record in records]


@router.get("/nearby", response_model=list[MachineryRentalResponse])
async def nearby_machinery_rentals(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=25, gt=0, le=250),
    category: str | None = Query(default=None, min_length=1),
    limit: int = Query(default=30, ge=1, le=100),
):
    records = await (MachineryRental.find({"category": category}) if category else MachineryRental.find_all()).to_list()
    ranked = []
    for item in records:
        distance = haversine_km(lat, lon, item.latitude, item.longitude)
        if distance is not None and distance <= radius_km:
            item.distance_km = distance
            ranked.append(item)
    ranked.sort(key=lambda item: item.distance_km if item.distance_km is not None else float("inf"))
    return [_to_response(record) for record in ranked[:limit]]


@router.get("/{rental_id}", response_model=MachineryRentalResponse)
async def get_machinery_rental(rental_id: str):
    rental = await MachineryRental.get(_to_object_id(rental_id))
    if not rental:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machinery rental not found")
    return _to_response(rental)


@router.put("/{rental_id}", response_model=MachineryRentalResponse)
async def update_machinery_rental(rental_id: str, payload: MachineryRentalUpdate):
    rental = await MachineryRental.get(_to_object_id(rental_id))
    if not rental:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machinery rental not found")
    updates = _normalise_aliases(payload.model_dump(exclude_unset=True))
    for field_name, value in updates.items():
        if value is not None:
            setattr(rental, field_name, value)
    await rental.save()
    return _to_response(rental)


@router.delete("/{rental_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_machinery_rental(rental_id: str):
    rental = await MachineryRental.get(_to_object_id(rental_id))
    if not rental:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machinery rental not found")
    await rental.delete()
