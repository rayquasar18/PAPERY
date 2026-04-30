"""Polling-first AI job submission and status endpoints."""

from __future__ import annotations

import uuid as uuid_pkg

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user
from app.core.db.session import get_session
from app.core.exceptions import NotFoundError
from app.models.user import User
from app.schemas.ai_job import (
    AIJobCreate,
    AIJobErrorResponse,
    AIJobRead,
    AIJobSubmitResponse,
    build_ai_job_error_response,
    build_ai_job_read,
    build_ai_job_submit_response,
)
from app.services.ai_job_service import AIJobService

router = APIRouter(prefix="/ai-jobs", tags=["ai-jobs"])


@router.post("", response_model=AIJobSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_ai_job(
    payload: AIJobCreate,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
) -> AIJobSubmitResponse:
    service = AIJobService(db)
    job = await service.submit_job(user, payload)
    return build_ai_job_submit_response(job)


@router.get(
    "/{job_uuid}",
    response_model=AIJobRead,
    responses={404: {"model": AIJobErrorResponse}},
)
async def get_ai_job_status(
    job_uuid: uuid_pkg.UUID,
    request: Request,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
) -> AIJobRead | JSONResponse:
    service = AIJobService(db)
    try:
        job = await service.get_job_status_for_user(user, job_uuid)
    except NotFoundError as exc:
        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=build_ai_job_error_response("NOT_FOUND", str(exc.detail), request_id).model_dump(),
        )
    return build_ai_job_read(job)
