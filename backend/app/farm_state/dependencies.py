from collections.abc import Generator

from fastapi import Header, HTTPException, status

from app.farm_state.store import FarmStateStore, safe_farmer_key


def get_farm_store(
    x_farmer_id: str | None = Header(default=None, alias="X-Farmer-ID"),
) -> Generator[FarmStateStore, None, None]:
    """Temporary local identity boundary; this is not authentication."""
    farmer_key = x_farmer_id or "demo"
    try:
        store = FarmStateStore(farmer_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    try:
        yield store
    finally:
        store.close()

