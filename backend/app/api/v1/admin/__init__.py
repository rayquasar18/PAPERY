"""Admin route group — all endpoints require superuser privileges.

The router-level dependency ``get_current_superuser`` is applied once here,
so every endpoint under /api/v1/admin/* automatically requires superuser.
No per-endpoint Depends needed.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_superuser
from app.api.v1.admin.rate_limits import router as rate_limits_router
from app.api.v1.admin.settings import router as settings_router
from app.api.v1.admin.tiers import router as tiers_router
from app.api.v1.admin.users import router as users_router

admin_router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_superuser)],
)

admin_router.include_router(users_router)
admin_router.include_router(tiers_router)
admin_router.include_router(rate_limits_router)
admin_router.include_router(settings_router)
