"""System setting schemas and allowlist registry.

The SETTINGS_REGISTRY defines all valid setting keys with their types,
categories, defaults, and optional validation constraints. Admin can only
edit values of keys listed here — cannot create arbitrary keys.
"""

from __future__ import annotations

import uuid as uuid_pkg
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Setting definition for the allowlist registry
# ---------------------------------------------------------------------------
@dataclass
class SettingDefinition:
    """Defines a valid system setting — type, category, default, and constraints."""

    type: type  # bool, int, str, list
    category: str
    default: Any
    description: str = ""
    min_value: int | None = None  # For int settings
    max_value: int | None = None  # For int settings
    allowed_values: list[str] | None = None  # For str settings (enum-like)


# ---------------------------------------------------------------------------
# Allowlist registry — code-defined setting keys
# ---------------------------------------------------------------------------
SETTINGS_REGISTRY: dict[str, SettingDefinition] = {
    "maintenance_mode": SettingDefinition(
        type=bool,
        category="general",
        default=False,
        description="When enabled, the application shows a maintenance page to non-admin users.",
    ),
    "max_upload_size_mb": SettingDefinition(
        type=int,
        category="storage",
        default=50,
        description="Maximum file upload size in megabytes.",
        min_value=1,
        max_value=500,
    ),
    "allowed_file_types": SettingDefinition(
        type=list,
        category="storage",
        default=["pdf", "docx", "xlsx", "pptx", "csv", "txt", "md"],
        description="List of allowed file extensions for document upload.",
    ),
    "default_tier": SettingDefinition(
        type=str,
        category="billing",
        default="free",
        description="Default tier slug assigned to new users.",
    ),
    "signup_enabled": SettingDefinition(
        type=bool,
        category="auth",
        default=True,
        description="When disabled, new user registration is blocked.",
    ),
}


def validate_setting_value(key: str, value: Any) -> Any:
    """Validate a setting value against its registry definition.

    Returns the validated value.
    Raises ValueError if the key is not in the registry or value is invalid.
    """
    if key not in SETTINGS_REGISTRY:
        raise ValueError(f"Unknown setting key: '{key}'. Only predefined keys are allowed.")

    defn = SETTINGS_REGISTRY[key]

    # Type check
    if defn.type is bool:
        if not isinstance(value, bool):
            raise ValueError(f"Setting '{key}' must be a boolean, got {type(value).__name__}")
    elif defn.type is int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"Setting '{key}' must be an integer, got {type(value).__name__}")
        if defn.min_value is not None and value < defn.min_value:
            raise ValueError(f"Setting '{key}' must be >= {defn.min_value}")
        if defn.max_value is not None and value > defn.max_value:
            raise ValueError(f"Setting '{key}' must be <= {defn.max_value}")
    elif defn.type is str:
        if not isinstance(value, str):
            raise ValueError(f"Setting '{key}' must be a string, got {type(value).__name__}")
        if defn.allowed_values and value not in defn.allowed_values:
            raise ValueError(f"Setting '{key}' must be one of {defn.allowed_values}")
    elif defn.type is list:
        if not isinstance(value, list):
            raise ValueError(f"Setting '{key}' must be a list, got {type(value).__name__}")

    return value


# ---------------------------------------------------------------------------
# API schemas
# ---------------------------------------------------------------------------
class SystemSettingRead(BaseModel):
    """System setting response."""

    model_config = ConfigDict(from_attributes=True)

    uuid: uuid_pkg.UUID
    key: str
    value: dict
    category: str
    description: str | None = None
    updated_at: datetime | None = None


class SystemSettingUpdate(BaseModel):
    """Update a system setting value — only the value field is editable."""

    value: Any = Field(..., description="The new value for the setting. Type must match the setting definition.")


class SystemSettingGroupedResponse(BaseModel):
    """All settings grouped by category."""

    settings: dict[str, list[SystemSettingRead]] = Field(
        default_factory=dict,
        description="Settings grouped by category name.",
    )
