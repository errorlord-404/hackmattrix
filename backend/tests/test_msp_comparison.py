from datetime import datetime, timezone

from app.models.market_price import MarketPrice
from app.models.msp import MSP
from app.services.msp_comparison import select_msp_market_comparison


def test_msp_comparison_selects_newest_mandi_observation_and_discloses_limits() -> None:
    at = datetime(2026, 9, 6, tzinfo=timezone.utc)
    result = select_msp_market_comparison(
        "Wheat",
        [MSP.model_construct(crop_name="Wheat", msp_price_per_quintal=2500, season="Rabi", marketing_year="2026-27", procurement_centres=[], fetched_at=at)],
        [
            MarketPrice.model_construct(crop_name="Wheat", mandi_name="A", price_per_quintal=2400, date=at, state="UP", district="A", source="manual"),
            MarketPrice.model_construct(crop_name="Wheat", mandi_name="A", price_per_quintal=2550, date=datetime(2026, 9, 7, tzinfo=timezone.utc), state="UP", district="A", source="AGMARKNET"),
        ],
    )
    assert result.msp.msp_price_per_quintal == 2500
    assert result.markets[0].difference_from_msp == 50
    assert "Procurement eligibility" in result.message
