from __future__ import annotations

from typing import Any

from app.core.config import settings


async def init_db() -> Any:
    """Initialize the optional Mongo reference catalog.

    Importing the standalone API never requires Mongo. Startup callers catch
    connection errors and expose the reference catalog as degraded.
    """
    from beanie import init_beanie
    from motor.motor_asyncio import AsyncIOMotorClient

    from app.models.crop import Crop
    from app.models.disease import Disease
    from app.models.farmer import Farmer
    from app.models.fertilizer import Fertilizer
    from app.models.gov_scheme import GovScheme
    from app.models.ingestion_run import IngestionRun
    from app.models.machinery_rental import MachineryRental
    from app.models.market_price import MarketPrice
    from app.models.marketplace_listing import MarketplaceListing
    from app.models.msp import MSP
    from app.models.seed import Seed

    client = AsyncIOMotorClient(
        settings.mongodb_url,
        serverSelectionTimeoutMS=settings.mongodb_connect_timeout_ms,
    )
    await init_beanie(
        database=client[settings.database_name],
        document_models=[
            Farmer, Crop, Disease, Fertilizer, MarketPrice, GovScheme, MSP,
            Seed, IngestionRun, MachineryRental, MarketplaceListing,
        ],
    )
    return client
