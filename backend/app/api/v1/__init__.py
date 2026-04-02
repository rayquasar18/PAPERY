"""API v1 router aggregator — all v1 routes are included here."""

from fastapi import APIRouter

from app.api.v1.health import router as health_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router, tags=["health"])
