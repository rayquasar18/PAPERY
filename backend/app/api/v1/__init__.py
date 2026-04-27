"""API v1 router aggregator — all v1 routes are included here."""

from fastapi import APIRouter

from app.api.v1.admin import admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.billing import router as billing_router
from app.api.v1.health import router as health_router
from app.api.v1.projects import router as projects_router
from app.api.v1.tiers import router as tiers_router
from app.api.v1.users import router as users_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router, tags=["health"])
api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(projects_router)
api_v1_router.include_router(tiers_router)
api_v1_router.include_router(billing_router)
api_v1_router.include_router(admin_router)
