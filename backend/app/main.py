from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import init_db
from app.core.config import settings
from app.routers.crop import router as crop_router
from app.routers.disease import router as disease_router
from app.routers.fertilizer import router as fertilizer_router
from app.routers.farmer import router as farmer_router
from app.routers.gov_scheme import router as gov_scheme_router
from app.routers.market_price import router as market_price_router
from app.routers.msp import router as msp_router
from app.routers.seed import router as seed_router
from app.routers.farm_state import router as farm_state_router
from app.routers.weather import router as weather_router
from app.routers.assistants import router as assistants_router
from app.routers.ingestion import router as ingestion_router
from app.routers.machinery_rental import router as machinery_rental_router
from app.routers.marketplace import router as marketplace_router
from app.routers.device_ingestion import router as device_ingestion_router
from app.routers.diagnostics import router as diagnostics_router
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = None
    app.state.reference_db_available = False
    app.state.reference_db_error = None
    try:
        try:
            client = await init_db()
            app.state.reference_db_available = True
        except Exception as exc:
            app.state.reference_db_error = str(exc)
        yield
    finally:
        if client is not None:
            client.close()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for now so frontend can connect
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


@app.middleware("http")
async def request_id_middleware(request, call_next):
    """Correlate UI/agent failures without exposing identity or secrets."""
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
app.include_router(farmer_router)
app.include_router(crop_router)
app.include_router(disease_router)
app.include_router(fertilizer_router)
app.include_router(market_price_router)
app.include_router(gov_scheme_router)
app.include_router(msp_router)
app.include_router(seed_router)
app.include_router(farm_state_router)
app.include_router(weather_router)
app.include_router(assistants_router)
app.include_router(ingestion_router)
app.include_router(machinery_rental_router)
app.include_router(marketplace_router)
app.include_router(device_ingestion_router)
app.include_router(diagnostics_router)


@app.get("/health", tags=["health"])
async def health():
    available = getattr(app.state, "reference_db_available", False)
    sarvam_available = bool(settings.SARVAM_API_KEY.strip())
    return {
        "status": "ok" if available else "degraded",
        "service": "kisansathi-backend",
        "farm_state": "available",
        "reference_database": "available" if available else "unavailable",
        "sarvam": "configured" if sarvam_available else "unconfigured",
        "sarvam_message": "Sarvam speech and translation routes are ready." if sarvam_available else "Set SARVAM_API_KEY to enable speech and translation.",
        "advisor": "codex_desktop_harness",
        "diagnosis": settings.DIAGNOSIS_PROVIDER,
    }
