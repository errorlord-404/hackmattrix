"""Official-source ingestion for the shared MongoDB reference database."""

from app.scraping.service import sync_universal_data

__all__ = ["sync_universal_data"]
