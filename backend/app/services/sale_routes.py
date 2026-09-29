"""Quote-backed sale comparison; never invent road distance or transport cost."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import Any

from app.schemas.market_price import SaleRouteCompareRequest, SaleRouteCompareResponse, SaleRouteResult
from app.services.market import calculate_net_realisation


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _name(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def _market_key(price: Any) -> tuple[str, ...]:
    return tuple(_name(getattr(price, field, None)) for field in ("state", "district", "mandi_name", "grade", "variety"))


def compare_sale_routes(
    request: SaleRouteCompareRequest,
    prices: list[Any],
    *,
    now: datetime | None = None,
) -> SaleRouteCompareResponse:
    checked_at = _utc(now or datetime.now(timezone.utc))
    price_by_id = {str(price.id): price for price in prices}
    latest_by_market: dict[tuple[str, ...], datetime] = {}
    for price in prices:
        observed = _utc(price.observed_at or price.date)
        key = _market_key(price)
        if key not in latest_by_market or observed > latest_by_market[key]:
            latest_by_market[key] = observed

    selected = [price_by_id.get(route.market_price_id) for route in request.routes]
    observed_classes = {
        (_name(price.grade), _name(price.variety)) for price in selected if price is not None
    }
    mixed_quality = len(observed_classes) > 1 and not (request.grade and request.variety)
    results: list[SaleRouteResult] = []
    for route, price in zip(request.routes, selected):
        missing: list[str] = []
        warnings: list[str] = []
        if price is None:
            missing.append("market_price_record")
        if route.road_distance_km is None or not (route.distance_source or "").strip():
            missing.append("sourced_road_distance")
        cost_fields = (
            "transport_cost_inr", "loading_cost_inr", "unloading_cost_inr",
            "market_fees_inr", "storage_cost_inr", "expected_spoilage_inr",
        )
        missing.extend(field for field in cost_fields if getattr(route, field) is None)
        if not (route.quote_source or "").strip() or route.quote_observed_at is None:
            missing.append("dated_transport_quote")
        elif checked_at - _utc(route.quote_observed_at) > timedelta(days=7):
            warnings.append("Transport quote is older than seven days; obtain a fresh quote.")
            missing.append("fresh_transport_quote")
        elif _utc(route.quote_observed_at) > checked_at + timedelta(hours=1):
            missing.append("valid_quote_time")

        observed = None
        revenue = None
        if price is not None:
            observed = _utc(price.observed_at or price.date)
            if not isfinite(price.price_per_quintal) or price.price_per_quintal <= 0:
                missing.append("valid_market_price")
            else:
                revenue = price.price_per_quintal * request.quantity_quintals
            if checked_at - observed > timedelta(days=request.max_price_age_days):
                missing.append("fresh_market_price")
                warnings.append("This mandi price is stale for a sale recommendation.")
            if observed > checked_at + timedelta(hours=1):
                missing.append("valid_price_time")
            if observed < latest_by_market[_market_key(price)]:
                missing.append("latest_market_price")
                warnings.append("A newer observation exists for this mandi, grade, and variety.")
            if not price.source_url or _name(price.source) in {"manual", "demo", "sample"}:
                missing.append("verifiable_price_source")
            if request.grade and _name(price.grade) != _name(request.grade):
                missing.append("matching_grade")
            if request.variety and _name(price.variety) != _name(request.variety):
                missing.append("matching_variety")
            if mixed_quality:
                missing.append("comparable_grade_and_variety")

        costs = sum(getattr(route, field) for field in cost_fields) if all(getattr(route, field) is not None for field in cost_fields) else None
        net = calculate_net_realisation(
            revenue, route.transport_cost_inr, route.loading_cost_inr,
            route.unloading_cost_inr, route.market_fees_inr,
            route.storage_cost_inr, route.expected_spoilage_inr,
        ) if not missing else None
        results.append(SaleRouteResult(
            market_price_id=route.market_price_id,
            mandi_name=price.mandi_name if price else None,
            district=price.district if price else None,
            state=price.state if price else None,
            grade=price.grade if price else None,
            variety=price.variety if price else None,
            price_per_quintal=price.price_per_quintal if price else None,
            price_observed_at=observed,
            price_source=price.source if price else None,
            price_source_url=price.source_url if price else None,
            road_distance_km=route.road_distance_km,
            distance_source=route.distance_source,
            quote_source=route.quote_source,
            quote_observed_at=route.quote_observed_at,
            sale_revenue_inr=revenue,
            disclosed_costs_inr=costs,
            net_realisation_inr=net,
            missing_evidence=missing,
            warnings=warnings,
        ))

    rankable = [item for item in results if item.net_realisation_inr is not None]
    if len(rankable) < 2:
        return SaleRouteCompareResponse(
            crop_name=request.crop_name, quantity_quintals=request.quantity_quintals,
            status="not_rankable", results=results,
            warnings=["At least two routes need fresh, comparable prices and complete dated distance/cost evidence before a destination can be recommended."],
        )
    rankable.sort(key=lambda item: item.net_realisation_inr, reverse=True)
    for rank, item in enumerate(rankable, start=1):
        item.rank = rank
    results.sort(key=lambda item: (item.rank is None, item.rank or 99))
    return SaleRouteCompareResponse(
        crop_name=request.crop_name, quantity_quintals=request.quantity_quintals,
        status="ranked", recommended_market_price_id=rankable[0].market_price_id,
        results=results,
        warnings=["Indicative net realisation only; confirm buyer acceptance, fees, and transport before travelling."],
    )
