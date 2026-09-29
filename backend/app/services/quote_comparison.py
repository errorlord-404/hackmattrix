from __future__ import annotations

from app.schemas.quote_comparison import MarketplaceQuote, QuoteComparisonItem, QuoteComparisonResponse


def compare_quotes(quotes: list[MarketplaceQuote]) -> QuoteComparisonResponse:
    """Rank explicit quotes by all disclosed costs, grouped by currency."""
    ordered = sorted(
        quotes,
        key=lambda quote: (
            quote.currency.upper(),
            quote.base_cost + quote.delivery_cost + quote.loading_cost + quote.unloading_cost + quote.additional_cost,
        ),
    )
    ranks: dict[str, int] = {}
    items: list[QuoteComparisonItem] = []
    for quote in ordered:
        currency = quote.currency.upper()
        ranks[currency] = ranks.get(currency, 0) + 1
        total = quote.base_cost + quote.delivery_cost + quote.loading_cost + quote.unloading_cost + quote.additional_cost
        items.append(QuoteComparisonItem(**quote.model_dump(), total_cost=total, rank=ranks[currency]))
    return QuoteComparisonResponse(
        comparison_basis=(
            "Ranked by disclosed base, delivery, loading, unloading, and additional costs. "
            "Only compare items with the same currency and unit; no exchange-rate, distance, tax, or unpublished cost is assumed."
        ),
        items=items,
    )
