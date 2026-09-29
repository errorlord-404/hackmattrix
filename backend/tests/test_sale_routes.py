from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app.models.market_price import MarketPrice
from app.routers.market_price import router as market_router
from app.schemas.market_price import SaleRouteCompareRequest
from app.services.sale_routes import compare_sale_routes


NOW = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)


def price(identifier, mandi, amount, *, days_old=1, grade="A", variety="Onion", source_url="https://example.gov/record"):
    observed = NOW - timedelta(days=days_old)
    return SimpleNamespace(
        id=identifier, crop_name="Onion", mandi_name=mandi, state="Maharashtra", district=mandi,
        grade=grade, variety=variety, price_per_quintal=amount, date=observed,
        observed_at=observed, fetched_at=observed, arrival_quintals=None,
        source="AGMARKNET", source_url=source_url,
    )


def route(identifier, transport, *, distance=100, quote_at=NOW):
    return {
        "market_price_id": identifier, "road_distance_km": distance,
        "distance_source": "farmer-provided route quote", "transport_cost_inr": transport,
        "loading_cost_inr": 100, "unloading_cost_inr": 100, "market_fees_inr": 100,
        "storage_cost_inr": 0, "expected_spoilage_inr": 0,
        "quote_source": "Carrier phone quote", "quote_observed_at": quote_at,
    }


def request(*routes, grade="A"):
    return SaleRouteCompareRequest(
        crop_name="Onion", quantity_quintals=10, grade=grade, variety="Onion", routes=list(routes),
    )


def test_lower_mandi_price_can_yield_higher_net_after_real_transport_quote():
    result = compare_sale_routes(
        request(route("pune", 1000, distance=210), route("mumbai", 6000, distance=330)),
        [price("pune", "Pune", 2000), price("mumbai", "Mumbai", 2300)], now=NOW,
    )
    assert result.status == "ranked"
    assert result.recommended_market_price_id == "pune"
    assert result.results[0].net_realisation_inr == 18700
    assert result.results[1].net_realisation_inr == 16700
    assert result.results[0].road_distance_km == 210


def test_missing_cost_or_stale_price_never_produces_a_destination_recommendation():
    missing_quote = route("pune", 1000)
    missing_quote.pop("market_fees_inr")
    result = compare_sale_routes(
        request(missing_quote, route("mumbai", 2000)),
        [price("pune", "Pune", 2000), price("mumbai", "Mumbai", 2300, days_old=30)], now=NOW,
    )
    assert result.status == "not_rankable"
    assert result.recommended_market_price_id is None
    assert all(item.net_realisation_inr is None for item in result.results)
    assert "market_fees_inr" in result.results[0].missing_evidence
    assert "fresh_market_price" in result.results[1].missing_evidence


def test_unverified_or_nonmatching_grade_is_not_ranked():
    result = compare_sale_routes(
        request(route("pune", 1000), route("mumbai", 1000)),
        [price("pune", "Pune", 2000, source_url=None), price("mumbai", "Mumbai", 2300, grade="B")], now=NOW,
    )
    assert result.status == "not_rankable"
    assert "verifiable_price_source" in result.results[0].missing_evidence
    assert "matching_grade" in result.results[1].missing_evidence


def test_superseded_price_record_is_not_ranked_even_when_recent():
    result = compare_sale_routes(
        request(route("old", 1000), route("mumbai", 1000)),
        [price("old", "Pune", 2400, days_old=2), price("new", "Pune", 2000, days_old=1), price("mumbai", "Mumbai", 2300)],
        now=NOW,
    )
    assert result.status == "not_rankable"
    assert "latest_market_price" in result.results[0].missing_evidence


def test_http_route_exposes_read_only_quote_comparison(monkeypatch):
    checked_at = datetime.now(timezone.utc) - timedelta(hours=1)

    class Query:
        async def to_list(self):
            values = [price("pune", "Pune", 2000), price("mumbai", "Mumbai", 2300)]
            for item in values:
                item.date = checked_at
                item.observed_at = checked_at
            return values

    monkeypatch.setattr(MarketPrice, "find", lambda *args, **kwargs: Query())
    app = FastAPI()
    app.include_router(market_router)
    with TestClient(app) as client:
        response = client.post("/market-prices/compare-routes", json=request(
            route("pune", 1000, quote_at=checked_at), route("mumbai", 6000, quote_at=checked_at)
        ).model_dump(mode="json"))
    assert response.status_code == 200
    assert response.json()["status"] == "ranked"
    assert response.json()["recommended_market_price_id"] == "pune"


def test_duplicate_route_or_nonfinite_quote_is_rejected():
    with pytest.raises(ValidationError):
        request(route("pune", 1000), route("pune", 1200))
    with pytest.raises(ValidationError):
        request(route("pune", float("inf")))


def test_summary_exposes_exact_latest_price_record_and_quality(monkeypatch):
    class Query:
        async def to_list(self):
            return [
                price("old", "Pune", 2400, days_old=2),
                price("new", "Pune", 2000, days_old=1),
                price("other-grade", "Pune", 2300, days_old=1, grade="B"),
            ]

    monkeypatch.setattr(MarketPrice, "find_all", lambda *args, **kwargs: Query())
    app = FastAPI()
    app.include_router(market_router)
    with TestClient(app) as client:
        response = client.get("/market-prices/summary", params={"crop": "Onion"})
    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == {"new", "other-grade"}
    assert {item["grade"] for item in response.json()} == {"A", "B"}
    assert all(item["source_url"] for item in response.json())
