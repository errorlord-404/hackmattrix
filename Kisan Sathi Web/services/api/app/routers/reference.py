from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, TypeVar

from beanie import PydanticObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.auth.dependencies import require_actor_scope
from kisansathi_auth.claims import ActorScope

from app.core.config import settings
from app.models.crop import Crop
from app.models.disease import Disease
from app.models.farmer import Farmer
from app.models.fertilizer import Fertilizer
from app.models.gov_scheme import GovScheme
from app.models.machinery_rental import MachineryRental
from app.models.market_price import MarketPrice
from app.models.marketplace_listing import MarketplaceListing
from app.models.msp import MSP
from app.models.seed import Seed
from app.schemas.crop import CropCreate, CropResponse, CropUpdate
from app.schemas.disease import DiseaseCreate, DiseaseResponse, DiseaseUpdate
from app.schemas.farmer import FarmerCreate, FarmerResponse, FarmerUpdate
from app.schemas.fertilizer import FertilizerCreate, FertilizerRecommendationRequest, FertilizerRecommendationResponse, FertilizerResponse, FertilizerUpdate
from app.schemas.gov_scheme import GovSchemeCreate, GovSchemeResponse, GovSchemeUpdate, SchemeEligibilityRequest, SchemeEligibilityResponse
from app.schemas.machinery_rental import MachineryRentalCreate, MachineryRentalResponse, MachineryRentalUpdate
from app.schemas.market_price import CompareMandisResponse, MandiComparisonResponse, MarketHistoryPoint, MarketPriceCreate, MarketPriceResponse, MarketPriceSummaryItem, MarketPriceUpdate, MarketTrendResponse
from app.schemas.marketplace_listing import MarketplaceDirectoryStatus, MarketplaceListingResponse
from app.schemas.msp import MSPCreate, MSPMarketComparisonItem, MSPMarketComparisonResponse, MSPResponse, MSPUpdate
from app.schemas.quote_comparison import QuoteComparisonRequest, QuoteComparisonResponse
from app.schemas.seed import SeedCreate, SeedRecommendationRequest, SeedRecommendationResponse, SeedResponse, SeedUpdate

router = APIRouter(tags=["reference"], dependencies=[Depends(require_actor_scope)])
T = TypeVar("T")


def _available(request: Request) -> None:
    if not getattr(request.app.state, "reference_db_available", False):
        raise HTTPException(status_code=503, detail={"code": "reference_database_unavailable", "message": "Shared reference data is temporarily unavailable.", "retryable": True})


def _oid(value: str, label: str) -> PydanticObjectId:
    try:
        return PydanticObjectId(value)
    except (InvalidId, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {label} ID") from exc


def _payload(item: Any) -> dict[str, Any]:
    value = item.model_dump(mode="json", exclude={"id"})
    return {"id": str(item.id), **value}


async def _one(model: Any, value: str, label: str, request: Request) -> Any:
    _available(request)
    item = await model.get(_oid(value, label))
    if not item:
        raise HTTPException(status_code=404, detail=f"{label.title()} not found")
    return item


@router.post("/crops", response_model=CropResponse, status_code=201)
async def create_crop(payload: CropCreate, request: Request):
    _available(request); item = Crop(**payload.model_dump()); await item.insert(); return _payload(item)

@router.get("/crops", response_model=list[CropResponse])
async def list_crops(request: Request, limit: int = Query(100, ge=1, le=500)):
    _available(request); return [_payload(x) for x in (await Crop.find_all().limit(limit).to_list())]

@router.get("/crops/{crop_id}", response_model=CropResponse)
async def get_crop(crop_id: str, request: Request): return _payload(await _one(Crop, crop_id, "crop", request))

@router.put("/crops/{crop_id}", response_model=CropResponse)
async def update_crop(crop_id: str, payload: CropUpdate, request: Request):
    item = await _one(Crop, crop_id, "crop", request)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    await item.save(); return _payload(item)

@router.delete("/crops/{crop_id}", status_code=204)
async def delete_crop(crop_id: str, request: Request): await (await _one(Crop, crop_id, "crop", request)).delete(); return Response(status_code=204)


@router.post("/diseases", response_model=DiseaseResponse, status_code=201)
async def create_disease(payload: DiseaseCreate, request: Request):
    _available(request); item = Disease(**payload.model_dump()); await item.insert(); return _payload(item)

@router.get("/diseases", response_model=list[DiseaseResponse])
async def list_diseases(request: Request, limit: int = Query(100, ge=1, le=500)):
    _available(request); return [_payload(x) for x in (await Disease.find_all().limit(limit).to_list())]

@router.get("/diseases/{disease_id}", response_model=DiseaseResponse)
async def get_disease(disease_id: str, request: Request): return _payload(await _one(Disease, disease_id, "disease", request))

@router.put("/diseases/{disease_id}", response_model=DiseaseResponse)
async def update_disease(disease_id: str, payload: DiseaseUpdate, request: Request):
    item = await _one(Disease, disease_id, "disease", request)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    await item.save(); return _payload(item)

@router.delete("/diseases/{disease_id}", status_code=204)
async def delete_disease(disease_id: str, request: Request): await (await _one(Disease, disease_id, "disease", request)).delete(); return Response(status_code=204)


@router.post("/farmers", response_model=FarmerResponse, status_code=201)
async def create_farmer(payload: FarmerCreate, request: Request):
    _available(request); item = Farmer(**payload.model_dump()); await item.insert(); return _payload(item)

@router.get("/farmers", response_model=list[FarmerResponse])
async def list_farmers(request: Request, limit: int = Query(100, ge=1, le=500)):
    _available(request); return [_payload(x) for x in (await Farmer.find_all().limit(limit).to_list())]

@router.get("/farmers/{farmer_id}", response_model=FarmerResponse)
async def get_farmer(farmer_id: str, request: Request): return _payload(await _one(Farmer, farmer_id, "farmer", request))

@router.put("/farmers/{farmer_id}", response_model=FarmerResponse)
async def update_farmer(farmer_id: str, payload: FarmerUpdate, request: Request):
    item = await _one(Farmer, farmer_id, "farmer", request)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    await item.save(); return _payload(item)

@router.delete("/farmers/{farmer_id}", status_code=204)
async def delete_farmer(farmer_id: str, request: Request): await (await _one(Farmer, farmer_id, "farmer", request)).delete(); return Response(status_code=204)


@router.post("/fertilizer", response_model=FertilizerResponse, status_code=201)
async def create_fertilizer(payload: FertilizerCreate, request: Request):
    _available(request); item = Fertilizer(**payload.model_dump()); await item.insert(); return _payload(item)

@router.get("/fertilizer", response_model=list[FertilizerResponse])
async def list_fertilizer(request: Request, limit: int = Query(100, ge=1, le=500)):
    _available(request); return [_payload(x) for x in (await Fertilizer.find_all().limit(limit).to_list())]

@router.post("/fertilizer/recommend", response_model=FertilizerRecommendationResponse)
async def recommend_fertilizer(payload: FertilizerRecommendationRequest, request: Request):
    _available(request); items = await Fertilizer.find_all().to_list()
    items = [x for x in items if payload.crop_name.casefold() in {c.casefold() for c in x.suitable_crops} and (not payload.fertilizer_type or x.type.casefold() == payload.fertilizer_type.casefold()) and (payload.max_budget_per_bag is None or x.subsidized_mrp <= payload.max_budget_per_bag)]
    return {"crop_name": payload.crop_name, "fertilizer_type": payload.fertilizer_type, "max_budget_per_bag": payload.max_budget_per_bag, "recommended_fertilizers": [_payload(x) for x in items[:50]]}

@router.get("/fertilizer/{fertilizer_id}", response_model=FertilizerResponse)
async def get_fertilizer(fertilizer_id: str, request: Request): return _payload(await _one(Fertilizer, fertilizer_id, "fertilizer", request))

@router.put("/fertilizer/{fertilizer_id}", response_model=FertilizerResponse)
async def update_fertilizer(fertilizer_id: str, payload: FertilizerUpdate, request: Request):
    item = await _one(Fertilizer, fertilizer_id, "fertilizer", request)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    await item.save(); return _payload(item)

@router.delete("/fertilizer/{fertilizer_id}", status_code=204)
async def delete_fertilizer(fertilizer_id: str, request: Request): await (await _one(Fertilizer, fertilizer_id, "fertilizer", request)).delete(); return Response(status_code=204)


def _state(value: str) -> str: return " ".join(value.strip().casefold().split())

@router.post("/gov-schemes", response_model=GovSchemeResponse, status_code=201)
async def create_scheme(payload: GovSchemeCreate, request: Request):
    _available(request); item = GovScheme(**payload.model_dump()); await item.insert(); return _payload(item)

@router.get("/gov-schemes", response_model=list[GovSchemeResponse])
async def list_schemes(request: Request, limit: int = Query(100, ge=1, le=500)):
    _available(request); return [_payload(x) for x in (await GovScheme.find_all().limit(limit).to_list())]

@router.get("/gov-schemes/by-state/{state}", response_model=list[GovSchemeResponse])
async def schemes_by_state(state: str, request: Request):
    _available(request); normalized = _state(state); items = await GovScheme.find_all().to_list()
    return [_payload(x) for x in items if not x.applicable_states or any(_state(v) == normalized or _state(v).startswith("india") for v in x.applicable_states)]

@router.post("/gov-schemes/check-eligibility", response_model=SchemeEligibilityResponse)
async def check_eligibility(payload: SchemeEligibilityRequest, request: Request):
    _available(request); normalized = _state(payload.farmer_state); required = {_state(x) for x in payload.eligibility_criteria}; items = await GovScheme.find_all().to_list()
    eligible = [x for x in items if (not x.applicable_states or any(_state(v) == normalized or _state(v).startswith("india") for v in x.applicable_states)) and required.issubset({_state(v) for v in x.eligibility_criteria})]
    return {"farmer_state": payload.farmer_state, "eligible_schemes": [_payload(x) for x in eligible[:100]]}

@router.get("/gov-schemes/{gov_scheme_id}", response_model=GovSchemeResponse)
async def get_scheme(gov_scheme_id: str, request: Request): return _payload(await _one(GovScheme, gov_scheme_id, "government scheme", request))

@router.put("/gov-schemes/{gov_scheme_id}", response_model=GovSchemeResponse)
async def update_scheme(gov_scheme_id: str, payload: GovSchemeUpdate, request: Request):
    item = await _one(GovScheme, gov_scheme_id, "government scheme", request)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    await item.save(); return _payload(item)

@router.delete("/gov-schemes/{gov_scheme_id}", status_code=204)
async def delete_scheme(gov_scheme_id: str, request: Request): await (await _one(GovScheme, gov_scheme_id, "government scheme", request)).delete(); return Response(status_code=204)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _market(item: MarketPrice) -> dict[str, Any]:
    value = item.model_dump(mode="json", exclude={"id"})
    value["observed_at"] = _utc(item.observed_at or item.date)
    value["fetched_at"] = _utc(item.fetched_at or item.date)
    return {"id": str(item.id), **value}


@router.post("/market-prices", response_model=MarketPriceResponse, status_code=201)
async def create_market_price(payload: MarketPriceCreate, request: Request):
    _available(request); values = payload.model_dump(); values["observed_at"] = values["observed_at"] or values["date"]; values["fetched_at"] = values["fetched_at"] or datetime.now(timezone.utc); item = MarketPrice(**values); await item.insert(); return _market(item)

@router.get("/market-prices", response_model=list[MarketPriceResponse])
async def list_market_prices(request: Request, limit: int = Query(100, ge=1, le=500)):
    _available(request); return [_market(x) for x in (await MarketPrice.find_all().limit(limit).to_list())]

@router.get("/market-prices/by-crop/{crop_name}", response_model=list[MarketPriceResponse])
async def market_prices_by_crop(crop_name: str, request: Request, limit: int = Query(100, ge=1, le=500)):
    _available(request); items = await MarketPrice.find_all().to_list(); return [_market(x) for x in items if x.crop_name.casefold() == crop_name.casefold()][:limit]

@router.get("/market-prices/summary", response_model=list[MarketPriceSummaryItem])
async def market_price_summary(request: Request, crop: str | None = None, limit: int = Query(100, ge=1, le=500)):
    _available(request); items = await MarketPrice.find_all().to_list(); latest: dict[tuple[str, str], MarketPrice] = {}
    for item in items:
        if crop and item.crop_name.casefold() != crop.casefold(): continue
        key = (item.crop_name.casefold(), item.mandi_name.casefold())
        if key not in latest or _utc(item.date) > _utc(latest[key].date): latest[key] = item
    now = datetime.now(timezone.utc)
    result = []
    for item in latest.values():
        fetched = _utc(item.fetched_at or item.date)
        result.append(MarketPriceSummaryItem(crop_name=item.crop_name, mandi_name=item.mandi_name, state=item.state, district=item.district, price_per_quintal=item.price_per_quintal, arrival_quintals=item.arrival_quintals, date=_utc(item.date), source=item.source, observed_at=_utc(item.observed_at or item.date), fetched_at=fetched, freshness_seconds=max(0, int((now-fetched).total_seconds()))))
    return sorted(result, key=lambda x: x.price_per_quintal, reverse=True)[:limit]

@router.get("/market-prices/history", response_model=list[MarketHistoryPoint])
async def market_price_history(request: Request, crop: str, mandi: str | None = None, from_date: datetime | None = Query(None, alias="from"), to_date: datetime | None = Query(None, alias="to"), limit: int = Query(500, ge=1, le=1000)):
    _available(request); items = await MarketPrice.find_all().to_list(); result = []
    for item in items:
        value = _utc(item.date)
        if item.crop_name.casefold() != crop.casefold() or (mandi and item.mandi_name.casefold() != mandi.casefold()) or (from_date and value < _utc(from_date)) or (to_date and value > _utc(to_date)): continue
        result.append(MarketHistoryPoint(mandi_name=item.mandi_name, date=value, price_per_quintal=item.price_per_quintal, arrival_quintals=item.arrival_quintals, source=item.source))
    return sorted(result, key=lambda x: x.date)[:limit]

@router.get("/market-prices/trend", response_model=MarketTrendResponse)
async def market_price_trend(request: Request, crop: str, mandi: str | None = None, days: int = Query(7, ge=2, le=90)):
    series = await market_price_history(request, crop, mandi, limit=1000)
    if not series: return MarketTrendResponse(crop_name=crop, mandi_name=mandi, days=days, series=[])
    anchor = series[-1].date; series = [x for x in series if x.date >= anchor - timedelta(days=days-1)]; current = series[-1].price_per_quintal; baseline = series[0].price_per_quintal; delta = current - baseline
    return MarketTrendResponse(crop_name=crop, mandi_name=mandi, days=days, current=current, delta=delta, delta_percent=delta / baseline * 100 if baseline else None, week_high=max(x.price_per_quintal for x in series), week_low=min(x.price_per_quintal for x in series), series=series)

@router.get("/market-prices/compare/{crop_name}", response_model=CompareMandisResponse)
async def compare_mandis(crop_name: str, request: Request, farmer_district: str, farmer_state: str, quantity_quintals: float = Query(1.0, gt=0), transport_cost: float | None = Query(None, ge=0), loading_cost: float | None = Query(None, ge=0), unloading_cost: float | None = Query(None, ge=0), market_fee_rate: float | None = Query(None, ge=0, le=1), storage_cost: float | None = Query(None, ge=0), expected_spoilage: float | None = Query(None, ge=0), cost_data_source: str = "configured-defaults"):
    _available(request); items = [x for x in await MarketPrice.find_all().to_list() if x.crop_name.casefold() == crop_name.casefold()]; result = []
    for item in items:
        if item.state.casefold() == farmer_state.casefold() and item.district.casefold() == farmer_district.casefold(): default_transport = 50.0
        elif item.state.casefold() == farmer_state.casefold(): default_transport = 150.0
        else: default_transport = 300.0
        transport = transport_cost if transport_cost is not None else default_transport; loading = loading_cost if loading_cost is not None else 200.0; unloading = unloading_cost or 0.0; fees = (market_fee_rate if market_fee_rate is not None else .02) * item.price_per_quintal * quantity_quintals; storage = storage_cost or 0.0; spoilage = expected_spoilage or 0.0; revenue = item.price_per_quintal * quantity_quintals; net = revenue - transport - loading - unloading - fees - storage - spoilage; fetched = _utc(item.fetched_at or item.date)
        result.append(MandiComparisonResponse(market_price_id=str(item.id), crop_name=item.crop_name, mandi_name=item.mandi_name, state=item.state, district=item.district, price_per_quintal=item.price_per_quintal, transport_cost=transport, loading_cost=loading, unloading_cost=unloading, market_fees=fees, storage_cost=storage, expected_spoilage=spoilage, sale_revenue=revenue, net_realisation=net, quantity_quintals=quantity_quintals, assumptions={"quantity_quintals": quantity_quintals, "transport_cost": transport, "loading_cost": loading, "market_fee_rate": fees/revenue if revenue else 0, "storage_cost": storage, "expected_spoilage": spoilage}, data_source=cost_data_source, observed_at=_utc(item.observed_at or item.date), fetched_at=fetched, freshness_seconds=max(0, int((datetime.now(timezone.utc)-fetched).total_seconds()))))
    return CompareMandisResponse(crop_name=crop_name, farmer_district=farmer_district, farmer_state=farmer_state, results=sorted(result, key=lambda x: x.net_realisation, reverse=True))

@router.get("/market-prices/{market_price_id}", response_model=MarketPriceResponse)
async def get_market_price(market_price_id: str, request: Request): return _market(await _one(MarketPrice, market_price_id, "market price", request))

@router.put("/market-prices/{market_price_id}", response_model=MarketPriceResponse)
async def update_market_price(market_price_id: str, payload: MarketPriceUpdate, request: Request):
    item = await _one(MarketPrice, market_price_id, "market price", request)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    await item.save(); return _market(item)

@router.delete("/market-prices/{market_price_id}", status_code=204)
async def delete_market_price(market_price_id: str, request: Request): await (await _one(MarketPrice, market_price_id, "market price", request)).delete(); return Response(status_code=204)


def _msp(item: MSP) -> dict[str, Any]: return {"id": str(item.id), **item.model_dump(mode="json", exclude={"id"})}

@router.post("/msp", response_model=MSPResponse, status_code=201)
async def create_msp(payload: MSPCreate, request: Request):
    _available(request); item = MSP(**payload.model_dump()); await item.insert(); return _msp(item)

@router.get("/msp", response_model=list[MSPResponse])
async def list_msp(request: Request, limit: int = Query(100, ge=1, le=500)):
    _available(request); return [_msp(x) for x in (await MSP.find_all().limit(limit).to_list())]

@router.get("/msp/by-crop/{crop_name}", response_model=list[MSPResponse])
async def msp_by_crop(crop_name: str, request: Request):
    _available(request); return [_msp(x) for x in await MSP.find(MSP.crop_name == crop_name).to_list()]

@router.get("/msp/compare-market", response_model=MSPMarketComparisonResponse)
async def compare_msp_market(request: Request, crop: str = Query(..., min_length=1)):
    _available(request); msps = [x for x in await MSP.find_all().to_list() if x.crop_name.casefold() == crop.casefold()]; selected = max(msps, key=lambda x: x.marketing_year, default=None); prices = [x for x in await MarketPrice.find_all().to_list() if x.crop_name.casefold() == crop.casefold()]
    return MSPMarketComparisonResponse(crop_name=crop, msp=_msp(selected) if selected else None, markets=[MSPMarketComparisonItem(mandi_name=x.mandi_name, state=x.state, district=x.district, market_price_per_quintal=x.price_per_quintal, msp_price_per_quintal=selected.msp_price_per_quintal if selected else 0, difference_from_msp=x.price_per_quintal-(selected.msp_price_per_quintal if selected else 0), observed_at=_utc(x.observed_at or x.date), source=x.source, source_url=x.source_url) for x in prices[:100]], message="Market observations are sourced records; comparison is not a procurement promise.")

@router.get("/msp/{msp_id}", response_model=MSPResponse)
async def get_msp(msp_id: str, request: Request): return _msp(await _one(MSP, msp_id, "msp", request))

@router.put("/msp/{msp_id}", response_model=MSPResponse)
async def update_msp(msp_id: str, payload: MSPUpdate, request: Request):
    item = await _one(MSP, msp_id, "msp", request)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    await item.save(); return _msp(item)

@router.delete("/msp/{msp_id}", status_code=204)
async def delete_msp(msp_id: str, request: Request): await (await _one(MSP, msp_id, "msp", request)).delete(); return Response(status_code=204)


def _seed(item: Seed) -> dict[str, Any]: return {"id": str(item.id), **item.model_dump(mode="json", exclude={"id"})}

@router.post("/seeds", response_model=SeedResponse, status_code=201)
async def create_seed(payload: SeedCreate, request: Request):
    _available(request); item = Seed(**payload.model_dump()); await item.insert(); return _seed(item)

@router.get("/seeds", response_model=list[SeedResponse])
async def list_seeds(request: Request, limit: int = Query(100, ge=1, le=500)):
    _available(request); return [_seed(x) for x in (await Seed.find_all().limit(limit).to_list())]

@router.post("/seeds/recommend", response_model=SeedRecommendationResponse)
async def recommend_seed(payload: SeedRecommendationRequest, request: Request):
    _available(request); items = [x for x in await Seed.find_all().to_list() if x.crop.casefold() == payload.crop.casefold() and (not payload.preferred_zone or x.recommended_zone.casefold() == payload.preferred_zone.casefold())]
    return {"crop": payload.crop, "preferred_zone": payload.preferred_zone, "disease_risk": payload.disease_risk, "recommended_seeds": [_seed(x) for x in items[:50]]}

@router.get("/seeds/{seed_id}", response_model=SeedResponse)
async def get_seed(seed_id: str, request: Request): return _seed(await _one(Seed, seed_id, "seed", request))

@router.put("/seeds/{seed_id}", response_model=SeedResponse)
async def update_seed(seed_id: str, payload: SeedUpdate, request: Request):
    item = await _one(Seed, seed_id, "seed", request)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    await item.save(); return _seed(item)

@router.delete("/seeds/{seed_id}", status_code=204)
async def delete_seed(seed_id: str, request: Request): await (await _one(Seed, seed_id, "seed", request)).delete(); return Response(status_code=204)


def _machinery(item: MachineryRental) -> dict[str, Any]:
    value = item.model_dump(mode="json", exclude={"id"})
    if not (value.get("location") or value.get("village")): value["location"] = value.get("district") or value.get("state") or "Location not provided by source"
    return {"id": str(item.id), **value}

@router.post("/machinery-rentals", response_model=MachineryRentalResponse, status_code=201)
async def create_machinery(payload: MachineryRentalCreate, request: Request):
    _available(request); values = payload.model_dump(); values["provider_name"] = values.get("provider_name") or values.get("owner_name"); values["owner_name"] = values.get("owner_name") or values["provider_name"]; values["location"] = values.get("location") or values.get("village"); values["village"] = values.get("village") or values["location"]; item = MachineryRental(**values); await item.insert(); return _machinery(item)

@router.get("/machinery-rentals", response_model=list[MachineryRentalResponse])
async def list_machinery(request: Request, category: str | None = None, district: str | None = None, state: str | None = None, limit: int = Query(100, ge=1, le=500)):
    _available(request); items = await MachineryRental.find_all().to_list(); return [_machinery(x) for x in items if (not category or x.category.casefold() == category.casefold()) and (not district or (x.district or "").casefold() == district.casefold()) and (not state or (x.state or "").casefold() == state.casefold())][:limit]

@router.get("/machinery-rentals/nearby", response_model=list[MachineryRentalResponse])
async def nearby_machinery(request: Request, lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180), radius_km: float = Query(25, gt=0, le=250), category: str | None = None, limit: int = Query(30, ge=1, le=100)):
    _available(request); items = await MachineryRental.find_all().to_list(); ranked = []
    for item in items:
        if category and item.category.casefold() != category.casefold() or item.latitude is None or item.longitude is None: continue
        distance = 111.2 * ((item.latitude-lat) ** 2 + ((item.longitude-lon) * 0.85) ** 2) ** .5
        if distance <= radius_km: item.distance_km = distance; ranked.append(item)
    return [_machinery(x) for x in sorted(ranked, key=lambda x: x.distance_km or 0)[:limit]]

@router.get("/machinery-rentals/{rental_id}", response_model=MachineryRentalResponse)
async def get_machinery(rental_id: str, request: Request): return _machinery(await _one(MachineryRental, rental_id, "machinery rental", request))

@router.put("/machinery-rentals/{rental_id}", response_model=MachineryRentalResponse)
async def update_machinery(rental_id: str, payload: MachineryRentalUpdate, request: Request):
    item = await _one(MachineryRental, rental_id, "machinery rental", request)
    values = payload.model_dump(exclude_unset=True)
    if "provider_name" in values or "owner_name" in values: values["provider_name"] = values.get("provider_name") or values.get("owner_name"); values["owner_name"] = values.get("owner_name") or values["provider_name"]
    if "location" in values or "village" in values: values["location"] = values.get("location") or values.get("village"); values["village"] = values.get("village") or values["location"]
    for key, value in values.items():
        if value is not None: setattr(item, key, value)
    await item.save(); return _machinery(item)

@router.delete("/machinery-rentals/{rental_id}", status_code=204)
async def delete_machinery(rental_id: str, request: Request): await (await _one(MachineryRental, rental_id, "machinery rental", request)).delete(); return Response(status_code=204)


@router.get("/marketplace/status", response_model=MarketplaceDirectoryStatus)
async def marketplace_status() -> MarketplaceDirectoryStatus:
    return MarketplaceDirectoryStatus(configured=bool(settings.reference_db_enabled), source_count=0, listing_types=[], message="Approved directory sources are available after reference database startup; listing freshness is shown per result.")


@router.post("/marketplace/compare-quotes", response_model=QuoteComparisonResponse)
async def compare_quotes(payload: QuoteComparisonRequest) -> QuoteComparisonResponse:
    items = []
    for rank, quote in enumerate(sorted(payload.quotes, key=lambda q: q.base_cost + q.delivery_cost + q.loading_cost + q.unloading_cost + q.additional_cost), 1):
        items.append({**quote.model_dump(), "total_cost": quote.base_cost + quote.delivery_cost + quote.loading_cost + quote.unloading_cost + quote.additional_cost, "rank": rank})
    return QuoteComparisonResponse(comparison_basis="Total disclosed cost in the supplied quote currency; no transaction is created.", items=items)


def _listing(item: MarketplaceListing, distance: float | None = None) -> dict[str, Any]:
    value = item.model_dump(mode="json", exclude={"id"})
    value["distance_km"] = distance
    return {"id": str(item.id), **value}


@router.get("/marketplace/listings", response_model=list[MarketplaceListingResponse])
async def list_listings(request: Request, listing_type: str | None = None, category: str | None = None, district: str | None = None, state: str | None = None, query: str | None = None, limit: int = Query(30, ge=1, le=100)):
    _available(request); allowed = {"machinery", "seed", "fertilizer", "logistics", "buyer", "exporter"}; normalized = listing_type.strip().casefold() if listing_type else None
    if normalized and normalized not in allowed: return []
    items = await MarketplaceListing.find_all().to_list(); pattern = re.compile(re.escape(query.strip()), re.I) if query else None; result = []
    for item in items:
        text = " ".join(filter(None, [item.title, item.category, item.provider_name, item.description, item.location]))
        if normalized and item.listing_type.casefold() != normalized or category and item.category != category or district and item.district != district or state and item.state != state or pattern and not pattern.search(text): continue
        result.append(item)
    result.sort(key=lambda x: x.fetched_at, reverse=True)
    return [_listing(x) for x in result[:limit]]


@router.get("/marketplace/nearby", response_model=list[MarketplaceListingResponse])
async def nearby_listings(request: Request, lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180), radius_km: float = Query(25, gt=0, le=250), listing_type: str | None = None, limit: int = Query(30, ge=1, le=100)):
    _available(request); items = await MarketplaceListing.find_all().to_list(); ranked = []
    for item in items:
        if listing_type and item.listing_type.casefold() != listing_type.casefold() or item.latitude is None or item.longitude is None: continue
        distance = 111.2 * ((item.latitude-lat) ** 2 + ((item.longitude-lon) * 0.85) ** 2) ** .5
        if distance <= radius_km: ranked.append((distance, item))
    return [_listing(item, distance) for distance, item in sorted(ranked, key=lambda pair: pair[0])[:limit]]
