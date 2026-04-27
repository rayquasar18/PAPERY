"""Project request/response schemas."""

from __future__ import annotations

import uuid as uuid_pkg
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Project name cannot be blank")
        return trimmed

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=160)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Project name cannot be blank")
        return trimmed

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: uuid_pkg.UUID
    owner_id: int
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class ProjectListItemRead(ProjectRead):
    relationship_type: str = "owned"
