from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories import UserPreferenceRepository, NotificationRepository
from app.schemas import (
    UserPreferenceRequest,
    UserPreferenceResponse,
    NotificationResponse,
)

router = APIRouter()

@router.post(
    "/users/{userId}/preferences",
    response_model=UserPreferenceResponse,
    status_code=200,
    summary="Set channel preferences for a user",
)
async def set_preferences(
    userId: str,
    pref: UserPreferenceRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    repo = UserPreferenceRepository(db)
    result = await repo.upsert(userId, pref)
    return result

@router.get(
    "/users/{userId}/preferences",
    response_model=UserPreferenceResponse,
    summary="Get channel preferences for a user",
)
async def get_preferences(
    userId: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    repo = UserPreferenceRepository(db)
    result = await repo.get_by_user_id(userId)
    
    if not result:
        # Fallback to default (all channels enabled) if user has no customized settings yet
        now = datetime.now(timezone.utc)
        return UserPreferenceResponse(
            userId=userId,
            emailEnabled=True,
            smsEnabled=True,
            pushEnabled=True,
            createdAt=now,
            updatedAt=now,
        )
    return result

@router.get(
    "/users/{userId}/notifications",
    response_model=list[NotificationResponse],
    summary="Get paginated notification history for a user",
)
async def get_history(
    userId: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> Any:
    repo = NotificationRepository(db)
    history = await repo.get_history(userId, limit=limit, offset=offset)
    return history
from typing import Any
