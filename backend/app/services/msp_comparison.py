from __future__ import annotations

from datetime import datetime, timezone

from app.models.market_price import MarketPrice
from app.models.msp import MSP
from app.schemas.msp import MSPMarketComparisonItem, MSPMarketComparisonResponse, MSPResponse


def as_msp_response(item: MSP) -> MSPResponse:
    return MSPResponse(id=str(item.id), **item.model_dump(exclude={"id"}))


def select_msp_market_comparison(crop_name: str, msps: list[MSP], prices: list[MarketPrice]) -> MSPMarketComparisonResponse:
    """Compare the newest source records without treating MSP as a procurement guarantee."""
    crop = crop_name.casefold()
    matching_msps = [item for item in msps if item.crop_name.casefold() == crop]
    latest_msp = max(matching_msps, key=lambda item: item.fetched_at or datetime.min.replace(tzinfo=timezone.utc), default=None)
    latest_by_mandi: dict[str, MarketPrice] = {}
    for price in prices:
        if price.crop_name.casefold() != crop:
            continue
        key = price.mandi_name.casefold()
        observed = price.observed_at or price.date
        previous = latest_by_mandi.get(key)
        if previous is None or observed > (previous.observed_at or previous.date):
            latest_by_mandi[key] = price
    if latest_msp is None:
        return MSPMarketComparisonResponse(crop_name=crop_name, msp=None, markets=[], message="No MSP record is available for this crop.")
    markets = []
    for price in latest_by_mandi.values():
        markets.append(MSPMarketComparisonItem(
            mandi_name=price.mandi_name,
            state=price.state,
            district=price.district,
            market_price_per_quintal=price.price_per_quintal,
            msp_price_per_quintal=latest_msp.msp_price_per_quintal,
            difference_from_msp=price.price_per_quintal - latest_msp.msp_price_per_quintal,
            observed_at=price.observed_at or price.date,
            source=price.source,
            source_url=price.source_url,
        ))
    markets.sort(key=lambda item: item.observed_at, reverse=True)
    return MSPMarketComparisonResponse(
        crop_name=crop_name,
        msp=as_msp_response(latest_msp),
        markets=markets,
        message="MSP is a reference price. Procurement eligibility, centre availability, grade and dates must be verified with official sources.",
    )
