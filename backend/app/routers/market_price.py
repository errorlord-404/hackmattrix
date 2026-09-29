from datetime import datetime, timedelta, timezone
from typing import List, Optional

from bson.errors import InvalidId
from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Query, status

from app.models.market_price import MarketPrice
from app.schemas.market_price import (
    CompareMandisResponse,
    MandiComparisonResponse,
    MarketPriceCreate,
    MarketPriceResponse,
    MarketPriceUpdate,
    MarketHistoryPoint,
    MarketPriceSummaryItem,
    MarketTrendResponse,
    SaleRouteCompareRequest,
    SaleRouteCompareResponse,
)
from app.services.market import calculate_net_realisation
from app.services.sale_routes import compare_sale_routes

router = APIRouter(prefix="/market-prices", tags=["market-prices"])

TRANSPORT_WITHIN_DISTRICT = 50.0
TRANSPORT_WITHIN_STATE = 150.0
TRANSPORT_OTHER_STATE = 300.0
LOADING_COST = 200.0
MARKET_FEE_RATE = 0.02


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _transport_cost(mandi_state: str, mandi_district: str, farmer_state: str, farmer_district: str) -> float:
    if mandi_state.strip().lower() == farmer_state.strip().lower() and mandi_district.strip().lower() == farmer_district.strip().lower():
        return TRANSPORT_WITHIN_DISTRICT
    if mandi_state.strip().lower() == farmer_state.strip().lower():
        return TRANSPORT_WITHIN_STATE
    return TRANSPORT_OTHER_STATE


def _to_response(market_price: MarketPrice) -> MarketPriceResponse:
    observed_at = _as_utc(market_price.observed_at or market_price.date)
    fetched_at = _as_utc(market_price.fetched_at or market_price.date)
    return MarketPriceResponse(
        id=str(market_price.id),
        crop_name=market_price.crop_name,
        mandi_name=market_price.mandi_name,
        price_per_quintal=market_price.price_per_quintal,
        date=market_price.date,
        state=market_price.state,
        district=market_price.district,
        arrival_quintals=market_price.arrival_quintals,
        source=market_price.source,
        observed_at=observed_at,
        fetched_at=fetched_at,
        min_price_per_quintal=market_price.min_price_per_quintal,
        max_price_per_quintal=market_price.max_price_per_quintal,
        variety=market_price.variety,
        grade=market_price.grade,
        source_record_id=market_price.source_record_id,
        source_url=market_price.source_url,
    )


def _to_object_id(market_price_id: str) -> PydanticObjectId:
    try:
        return PydanticObjectId(market_price_id)
    except (InvalidId, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid market price ID")


@router.post("", response_model=MarketPriceResponse, status_code=status.HTTP_201_CREATED)
async def create_market_price(payload: MarketPriceCreate):
    values = payload.model_dump()
    values["observed_at"] = values["observed_at"] or values["date"]
    values["fetched_at"] = values["fetched_at"] or datetime.now(timezone.utc)
    market_price = MarketPrice(**values)
    await market_price.insert()
    return _to_response(market_price)


@router.get("", response_model=List[MarketPriceResponse])
async def list_market_prices():
    market_prices = await MarketPrice.find_all().to_list()
    return [_to_response(market_price) for market_price in market_prices]


@router.get("/by-crop/{crop_name}", response_model=List[MarketPriceResponse])
async def list_market_prices_by_crop(crop_name: str):
    market_prices = await MarketPrice.find(MarketPrice.crop_name == crop_name).to_list()
    return [_to_response(market_price) for market_price in market_prices]


@router.get("/summary", response_model=List[MarketPriceSummaryItem])
async def market_price_summary(
    crop: Optional[str] = Query(default=None),
    district: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
):
    prices = await MarketPrice.find_all().to_list()
    latest: dict[str, MarketPrice] = {}
    for price in prices:
        if crop and price.crop_name.lower() != crop.lower():
            continue
        if district and price.district.lower() != district.lower():
            continue
        if state and price.state.lower() != state.lower():
            continue
        key = ":".join((price.crop_name, price.state, price.district, price.mandi_name, price.grade or "", price.variety or "")).casefold()
        if key not in latest or _as_utc(price.observed_at or price.date) > _as_utc(latest[key].observed_at or latest[key].date):
            latest[key] = price
    now = datetime.now(timezone.utc)
    results = []
    for price in latest.values():
        fetched_at = _as_utc(price.fetched_at or price.date)
        results.append(MarketPriceSummaryItem(
            id=str(price.id),
            crop_name=price.crop_name, mandi_name=price.mandi_name, state=price.state, district=price.district,
            price_per_quintal=price.price_per_quintal, arrival_quintals=price.arrival_quintals, date=_as_utc(price.date),
            source=price.source, observed_at=price.observed_at or price.date, fetched_at=fetched_at,
            freshness_seconds=max(0, int((now - fetched_at).total_seconds())),
            grade=price.grade, variety=price.variety, source_url=price.source_url,
        ))
    return sorted(results, key=lambda item: item.price_per_quintal, reverse=True)


@router.get("/history", response_model=List[MarketHistoryPoint])
async def market_price_history(
    crop: str = Query(..., min_length=1),
    mandi: Optional[str] = Query(default=None),
    from_date: Optional[datetime] = Query(default=None, alias="from"),
    to_date: Optional[datetime] = Query(default=None, alias="to"),
):
    prices = await MarketPrice.find_all().to_list()
    results = []
    for price in prices:
        if price.crop_name.lower() != crop.lower() or (mandi and price.mandi_name.lower() != mandi.lower()):
            continue
        if from_date and _as_utc(price.date) < _as_utc(from_date):
            continue
        if to_date and _as_utc(price.date) > _as_utc(to_date):
            continue
        results.append(MarketHistoryPoint(mandi_name=price.mandi_name, date=_as_utc(price.date),
                                          price_per_quintal=price.price_per_quintal,
                                          arrival_quintals=price.arrival_quintals, source=price.source))
    return sorted(results, key=lambda item: item.date)


@router.get("/trend", response_model=MarketTrendResponse)
async def market_price_trend(
    crop: str = Query(..., min_length=1),
    mandi: Optional[str] = Query(default=None),
    days: int = Query(default=7, ge=2, le=90),
):
    prices = await MarketPrice.find_all().to_list()
    filtered = [price for price in prices if price.crop_name.lower() == crop.lower() and (not mandi or price.mandi_name.lower() == mandi.lower())]
    if not filtered:
        return MarketTrendResponse(crop_name=crop, mandi_name=mandi, days=days, series=[])
    anchor = max((_as_utc(price.date) for price in filtered))
    cutoff = anchor - timedelta(days=days - 1)
    series = [price for price in filtered if _as_utc(price.date) >= cutoff]
    series.sort(key=lambda item: _as_utc(item.date))
    points = [MarketHistoryPoint(mandi_name=item.mandi_name, date=_as_utc(item.date), price_per_quintal=item.price_per_quintal,
                                 arrival_quintals=item.arrival_quintals, source=item.source) for item in series]
    current = points[-1].price_per_quintal if points else None
    baseline = points[0].price_per_quintal if points else None
    delta = current - baseline if current is not None and baseline is not None else None
    return MarketTrendResponse(crop_name=crop, mandi_name=mandi, days=days, current=current, delta=delta,
                               delta_percent=(delta / baseline * 100) if delta is not None and baseline else None,
                               week_high=max(point.price_per_quintal for point in points) if points else None,
                               week_low=min(point.price_per_quintal for point in points) if points else None,
                               series=points)


@router.get("/compare/{crop_name}", response_model=CompareMandisResponse)
async def compare_mandis(
    crop_name: str,
    farmer_district: str = Query(..., min_length=1),
    farmer_state: str = Query(..., min_length=1),
    quantity_quintals: float = Query(default=1.0, gt=0),
    transport_cost: Optional[float] = Query(default=None, ge=0),
    loading_cost: Optional[float] = Query(default=None, ge=0),
    unloading_cost: Optional[float] = Query(default=None, ge=0),
    market_fee_rate: Optional[float] = Query(default=None, ge=0, le=1),
    storage_cost: Optional[float] = Query(default=None, ge=0),
    expected_spoilage: Optional[float] = Query(default=None, ge=0),
    cost_data_source: str = Query(default="configured-defaults", min_length=1),
):
    market_prices = await MarketPrice.find({"crop_name": crop_name}).to_list()

    # One newest observation per comparable market/grade/variety. Historic
    # observations belong in the history route, not side-by-side sale scenarios.
    latest: dict[tuple[str, ...], MarketPrice] = {}
    for price in market_prices:
        key = tuple((value or "").strip().casefold() for value in (
            price.state, price.district, price.mandi_name, price.grade, price.variety,
        ))
        if key not in latest or _as_utc(price.observed_at or price.date) > _as_utc(latest[key].observed_at or latest[key].date):
            latest[key] = price

    results = []
    for market_price in latest.values():
        resolved_transport_cost = transport_cost if transport_cost is not None else _transport_cost(
            market_price.state,
            market_price.district,
            farmer_state,
            farmer_district,
        )
        resolved_loading_cost = loading_cost if loading_cost is not None else LOADING_COST
        resolved_unloading_cost = unloading_cost if unloading_cost is not None else 0.0
        resolved_market_fee_rate = market_fee_rate if market_fee_rate is not None else MARKET_FEE_RATE
        resolved_storage_cost = storage_cost if storage_cost is not None else 0.0
        resolved_expected_spoilage = expected_spoilage if expected_spoilage is not None else 0.0
        sale_revenue = market_price.price_per_quintal * quantity_quintals
        market_fees = resolved_market_fee_rate * sale_revenue
        net_realisation = calculate_net_realisation(
            sale_revenue=sale_revenue,
            transport_cost=resolved_transport_cost,
            loading_cost=resolved_loading_cost,
            unloading_cost=resolved_unloading_cost,
            market_fees=market_fees,
            storage_cost=resolved_storage_cost,
            expected_spoilage=resolved_expected_spoilage,
        )
        observed_at = _as_utc(market_price.observed_at or market_price.date)
        fetched_at = _as_utc(market_price.fetched_at or market_price.date)
        assumptions = {
            "quantity_quintals": quantity_quintals,
            "transport_cost": resolved_transport_cost,
            "loading_cost": resolved_loading_cost,
            "unloading_cost": resolved_unloading_cost,
            "market_fee_rate": resolved_market_fee_rate,
            "storage_cost": resolved_storage_cost,
            "expected_spoilage": resolved_expected_spoilage,
        }
        results.append(
            MandiComparisonResponse(
                market_price_id=str(market_price.id),
                crop_name=market_price.crop_name,
                mandi_name=market_price.mandi_name,
                state=market_price.state,
                district=market_price.district,
                price_per_quintal=market_price.price_per_quintal,
                transport_cost=resolved_transport_cost,
                loading_cost=resolved_loading_cost,
                unloading_cost=resolved_unloading_cost,
                market_fees=market_fees,
                storage_cost=resolved_storage_cost,
                expected_spoilage=resolved_expected_spoilage,
                sale_revenue=sale_revenue,
                net_realisation=net_realisation,
                quantity_quintals=quantity_quintals,
                assumptions=assumptions,
                data_source=cost_data_source,
                observed_at=observed_at,
                fetched_at=fetched_at,
                freshness_seconds=max(0, int((datetime.now(timezone.utc) - fetched_at).total_seconds())),
            )
        )

    results.sort(key=lambda item: (item.state.casefold(), item.district.casefold(), item.mandi_name.casefold()))
    return CompareMandisResponse(
        crop_name=crop_name,
        farmer_district=farmer_district,
        farmer_state=farmer_state,
        results=results,
        warnings=[
            "Illustrative only: flat district/state transport defaults are not road distances or provider quotes.",
            "Prices may be stale or for different grades or varieties; use compare-routes with fresh comparable prices and dated quotes before choosing a destination.",
        ],
    )


@router.post("/compare-routes", response_model=SaleRouteCompareResponse)
async def compare_sale_route_quotes(payload: SaleRouteCompareRequest):
    """Read-only comparison; the caller supplies road distance and actual cost quotes."""
    market_prices = await MarketPrice.find({"crop_name": payload.crop_name}).to_list()
    return compare_sale_routes(payload, market_prices)


@router.get("/{market_price_id}", response_model=MarketPriceResponse)
async def get_market_price(market_price_id: str):
    market_price = await MarketPrice.get(_to_object_id(market_price_id))
    if not market_price:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market price not found")
    return _to_response(market_price)


@router.put("/{market_price_id}", response_model=MarketPriceResponse)
async def update_market_price(market_price_id: str, payload: MarketPriceUpdate):
    market_price = await MarketPrice.get(_to_object_id(market_price_id))
    if not market_price:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market price not found")

    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        setattr(market_price, field_name, value)
    await market_price.save()
    return _to_response(market_price)


@router.delete("/{market_price_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_market_price(market_price_id: str):
    market_price = await MarketPrice.get(_to_object_id(market_price_id))
    if not market_price:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market price not found")
    await market_price.delete()
