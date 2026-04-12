"""Admin system settings endpoints — view and edit runtime configuration."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.session import get_session
from app.schemas.system_setting import (
    SystemSettingGroupedResponse,
    SystemSettingRead,
    SystemSettingUpdate,
)
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["admin-settings"])


@router.get("", response_model=SystemSettingGroupedResponse)
async def list_settings(
    db: AsyncSession = Depends(get_session),
) -> SystemSettingGroupedResponse:
    """List all system settings grouped by category. Superuser only."""
    service = SettingsService(db)
    grouped = await service.get_all_settings()
    return SystemSettingGroupedResponse(settings=grouped)


@router.get("/{key}", response_model=SystemSettingRead)
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_session),
) -> SystemSettingRead:
    """Get a single system setting by key. Superuser only."""
    service = SettingsService(db)
    setting = await service.get_setting(key)
    return SystemSettingRead.model_validate(setting)


@router.patch("/{key}", response_model=SystemSettingRead)
async def update_setting(
    key: str,
    data: SystemSettingUpdate,
    db: AsyncSession = Depends(get_session),
) -> SystemSettingRead:
    """Update a system setting value. Superuser only.

    The value must match the type defined in the settings registry
    (bool, int, str, or list depending on the key).
    """
    service = SettingsService(db)
    updated = await service.update_setting(key, data.value)
    return SystemSettingRead.model_validate(updated)
