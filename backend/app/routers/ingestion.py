import hmac

from fastapi import APIRouter, Header, HTTPException, Query, Request, status

from app.core.config import settings
from app.models.ingestion_run import IngestionRun
from app.schemas.ingestion import IngestionRunResponse
from app.scraping.service import SUPPORTED_SOURCES, sync_universal_data


router = APIRouter(prefix="/internal/universal-data", tags=["internal-universal-data"])


def _authorize(token: str | None) -> None:
    configured = settings.SCRAPER_WEBHOOK_TOKEN
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SCRAPER_WEBHOOK_TOKEN is not configured",
        )
    if token is None or not hmac.compare_digest(token, configured):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid ingestion token")


def _to_response(run: IngestionRun) -> IngestionRunResponse:
    return IngestionRunResponse(
        id=str(run.id), trigger=run.trigger, sources=run.sources, status=run.status,
        started_at=run.started_at, completed_at=run.completed_at, stats=run.stats,
        errors=run.errors, source_urls=run.source_urls,
    )


@router.post("/sync", response_model=IngestionRunResponse)
async def run_universal_data_sync(
    request: Request,
    sources: str = Query(default=",".join(sorted(SUPPORTED_SOURCES))),
    ingestion_token: str | None = Header(default=None, alias="X-Ingestion-Token"),
):
    _authorize(ingestion_token)
    if not getattr(request.app.state, "reference_db_available", False):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Reference database is unavailable")
    requested = [value.strip() for value in sources.split(",") if value.strip()]
    try:
        return await sync_universal_data(sources=requested, trigger="n8n")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/runs", response_model=list[IngestionRunResponse])
async def list_universal_data_runs(
    limit: int = Query(default=20, ge=1, le=100),
    ingestion_token: str | None = Header(default=None, alias="X-Ingestion-Token"),
):
    _authorize(ingestion_token)
    runs = await IngestionRun.find_all().sort(-IngestionRun.started_at).limit(limit).to_list()
    return [_to_response(run) for run in runs]
