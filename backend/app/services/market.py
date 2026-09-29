def calculate_net_realisation(
    sale_revenue: float,
    transport_cost: float,
    loading_cost: float,
    unloading_cost: float,
    market_fees: float,
    storage_cost: float,
    expected_spoilage: float,
) -> float:
    """Apply the documented net-realisation formula without hidden costs."""
    return sale_revenue - transport_cost - loading_cost - unloading_cost - market_fees - storage_cost - expected_spoilage
