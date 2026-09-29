from app.schemas.quote_comparison import MarketplaceQuote
from app.services.quote_comparison import compare_quotes


def test_compare_quotes_uses_only_disclosed_costs_and_keeps_currency_groups() -> None:
    response = compare_quotes([
        MarketplaceQuote(provider_name="A", title="Tractor", base_cost=1000, delivery_cost=200, currency="INR", unit="day"),
        MarketplaceQuote(provider_name="B", title="Tractor", base_cost=1100, currency="INR", unit="day"),
        MarketplaceQuote(provider_name="C", title="Tractor", base_cost=10, currency="USD", unit="day"),
    ])
    assert [(item.provider_name, item.total_cost, item.rank) for item in response.items] == [
        ("B", 1100.0, 1), ("A", 1200.0, 2), ("C", 10.0, 1),
    ]
    assert "unpublished cost" in response.comparison_basis
