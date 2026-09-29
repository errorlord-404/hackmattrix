"""Compatibility import for callers that used the baseline router module."""

from app.routers.domain import get_farm_store, router

__all__ = ["get_farm_store", "router"]
