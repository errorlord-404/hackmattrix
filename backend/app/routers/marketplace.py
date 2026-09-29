from __future__ import annotations

import re

from fastapi import APIRouter, Query

from app.models.marketplace_listing import MarketplaceListing
from app.schemas.marketplace_listing import MarketplaceDirectoryStatus, MarketplaceListingResponse
from app.schemas.quote_comparison import QuoteComparisonRequest, QuoteComparisonResponse
from app.services.quote_comparison import compare_quotes
from app.services.geo import haversine_km, normalize_admin
from app.scraping.service import _marketplace_sources


router = APIRouter(prefix="/marketplace", tags=["marketplace"])

_ALLOWED_TYPES = {"machinery", "seed", "fertilizer", "logistics", "buyer", "exporter"}


@router.get("/status", response_model=MarketplaceDirectoryStatus)
async def marketplace_directory_status():
    """Expose setup state without claiming source stock or listing availability."""
    try:
        sources = _marketplace_sources()
    except ValueError as exc:
        return MarketplaceDirectoryStatus(configured=False, source_count=0, listing_types=[], message=f"Directory configuration needs correction: {exc}")
    if not sources:
        return MarketplaceDirectoryStatus(configured=False, source_count=0, listing_types=[], message="No approved public directory sources are configured.")
    return MarketplaceDirectoryStatus(
        configured=True,
        source_count=len(sources),
        listing_types=sorted({source["listing_type"] for source in sources}),
        message="Approved directory sources are configured. Listing freshness is shown per result after ingestion.",
    )


@router.post("/compare-quotes", response_model=QuoteComparisonResponse)
async def compare_marketplace_quotes(payload: QuoteComparisonRequest):
    """Compare farmer/supplier-provided quotes without creating a transaction."""
    return compare_quotes(payload.quotes)


def _response(item: MarketplaceListing) -> MarketplaceListingResponse:
    return MarketplaceListingResponse(id=str(item.id), **item.model_dump(exclude={"id"}))


def _nearby_response(item: MarketplaceListing, distance_km: float | None) -> MarketplaceListingResponse:
    payload = item.model_dump(exclude={"id"})
    payload["distance_km"] = distance_km
    return MarketplaceListingResponse(id=str(item.id), **payload)


@router.get("/listings", response_model=list[MarketplaceListingResponse])
async def list_marketplace_listings(
    listing_type: str | None = Query(default=None, max_length=30),
    category: str | None = Query(default=None, max_length=100),
    district: str | None = Query(default=None, max_length=100),
    state: str | None = Query(default=None, max_length=100),
    query: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=30, ge=1, le=100),
):
    """Search verified public-directory records. No transaction can be created here."""
    normalized_type = listing_type.strip().casefold() if listing_type else None
    if normalized_type and normalized_type not in _ALLOWED_TYPES:
        return []
    filters = []
    if normalized_type:
        filters.append(MarketplaceListing.listing_type == normalized_type)
    if category:
        filters.append(MarketplaceListing.category == category)
    district = normalize_admin(district)
    state = normalize_admin(state)
    if district:
        filters.append(MarketplaceListing.district == district)
    if state:
        filters.append(MarketplaceListing.state == state)
    records = await MarketplaceListing.find(*filters).sort(-MarketplaceListing.fetched_at).to_list()
    if query:
        matcher = re.compile(re.escape(query.strip()), re.IGNORECASE)
        records = [
            item for item in records
            if matcher.search(" ".join(filter(None, [item.title, item.category, item.provider_name, item.description, item.location])))
        ]
    records.sort(key=lambda item: (item.record_kind != "provider_listing", -(item.fetched_at.timestamp() if item.fetched_at else 0)))
    return [_response(item) for item in records[:limit]]


@router.get("/nearby", response_model=list[MarketplaceListingResponse])
async def nearby_marketplace_listings(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=25, gt=0, le=250),
    listing_type: str | None = Query(default=None, max_length=30),
    limit: int = Query(default=30, ge=1, le=100),
):
    """Return bounded, source-attributed listings near a farmer-selected field."""
    normalized_type = listing_type.strip().casefold() if listing_type else None
    if normalized_type and normalized_type not in _ALLOWED_TYPES:
        return []
    records = await MarketplaceListing.find(MarketplaceListing.listing_type == normalized_type).to_list() if normalized_type else await MarketplaceListing.find_all().to_list()
    ranked = []
    for item in records:
        distance = haversine_km(lat, lon, item.latitude, item.longitude)
        if distance is not None and distance <= radius_km:
            ranked.append((distance, item))
    ranked.sort(key=lambda pair: pair[0])
    return [_nearby_response(item, distance) for distance, item in ranked[:limit]]
