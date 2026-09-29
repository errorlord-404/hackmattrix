from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.models.farmer import Farmer
from app.models.crop import Crop
from app.models.disease import Disease
from app.models.fertilizer import Fertilizer
from app.models.gov_scheme import GovScheme
from app.models.market_price import MarketPrice
from app.models.msp import MSP
from app.models.seed import Seed
from app.models.ingestion_run import IngestionRun
from app.models.machinery_rental import MachineryRental
from app.models.marketplace_listing import MarketplaceListing


async def init_db():
    client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        serverSelectionTimeoutMS=settings.MONGODB_CONNECT_TIMEOUT_MS,
    )
    await init_beanie(
        database=client[settings.DATABASE_NAME],
        document_models=[Farmer, Crop, Disease, Fertilizer, MarketPrice, GovScheme, MSP, Seed, IngestionRun, MachineryRental, MarketplaceListing],
    )
    return client
