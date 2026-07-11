import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.repositories import (
    NotificationRepository,
    TemplateRepository,
    UserPreferenceRepository,
)
from app.schemas import NotificationRequest, NotificationResponse
from app.services import (
    TemplateService,
    TemplateValidationError,
    RateLimiterService,
    RateLimitExceededError,
    IdempotencyService,
    IdempotencyLockError,
    IdempotencyPayloadConflictError,
    PreferenceService,
)
from app.workers.tasks import send_notification_delivery

router = APIRouter()

@router.post(
    "/notifications",
    response_model=NotificationResponse,
    status_code=201,
    summary="Send a notification",
)
async def send_notification(
    request: Request,
    response: Response,
    payload_in: NotificationRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> Any:
    # 1. Handle Idempotency Key
    idempotency_key = request.headers.get("x-idempotency-key")
    idempotency_service = IdempotencyService(redis)
    payload_dict = payload_in.model_dump(mode="json")

    if idempotency_key:
        try:
            cached_res = await idempotency_service.check_or_lock(idempotency_key, payload_dict)
            if cached_res:
                # Key already completed, return original cached response
                response.status_code = cached_res["status_code"]
                return cached_res["body"]
        except IdempotencyPayloadConflictError as err:
            # 409 Conflict per spec: same key with different payload
            raise HTTPException(status_code=409, detail=str(err))
        except IdempotencyLockError as err:
            # Request already in progress
            raise HTTPException(status_code=409, detail=str(err))

    try:
        # 2. Rate Limiting
        rate_limiter = RateLimiterService(redis)
        await rate_limiter.check_rate_limit(payload_in.user_id)

        # 3. Resolve and Validate Template
        template_repo = TemplateRepository(db)
        template = await template_repo.get_by_name(payload_in.template_name)
        if not template:
            raise HTTPException(
                status_code=400,
                detail=f"Template '{payload_in.template_name}' not found."
            )

        template_service = TemplateService()
        try:
            # Run validation (raising validation error on missing variables)
            template_service.render_subject_and_body(
                template.content,
                template.subject,
                payload_in.variables,
            )
        except TemplateValidationError as err:
            raise HTTPException(status_code=400, detail=str(err))

        # 4. Check User Preference & Filter Channels
        preference_repo = UserPreferenceRepository(db)
        user_pref = await preference_repo.get_by_user_id(payload_in.user_id)
        
        pref_service = PreferenceService()
        filtered_channels = pref_service.filter_channels(user_pref, payload_in.channels)

        # 5. Persist Notification Metadata (PENDING State first)
        notification_repo = NotificationRepository(db)
        notification = await notification_repo.create_notification(
            user_id=payload_in.user_id,
            template_id=template.id,
            template_variables=payload_in.variables,
            priority=payload_in.priority.value,
            idempotency_key=idempotency_key,
        )

        deliveries_created = []
        for channel in filtered_channels:
            delivery = await notification_repo.create_delivery(
                notification_id=notification.id,
                channel=channel.value,
                status="PENDING",
            )
            deliveries_created.append(delivery)

        # Commit DB records before queuing to background workers (Reliability)
        await notification_repo.commit()

        # 6. Queue Background Deliveries
        for delivery in deliveries_created:
            # Route to Celery queue dynamically based on priority
            queue_name = payload_in.priority.value.lower()
            if queue_name == "normal":
                queue_name = "default"

            send_notification_delivery.apply_async(
                args=[str(delivery.id)],
                queue=queue_name,
            )

        # Re-fetch notification with preloaded relationships to construct response
        fresh_notification = await notification_repo.get_by_id(notification.id)
        if not fresh_notification:
            raise HTTPException(status_code=500, detail="Notification creation failed on load.")

        response_body = NotificationResponse.model_validate(fresh_notification).model_dump(mode="json")

        # 7. Save to Idempotency Cache
        if idempotency_key:
            await idempotency_service.save_response(
                key=idempotency_key,
                payload=payload_dict,
                status_code=201,
                response_body=response_body,
            )

        return response_body

    except HTTPException:
        # Re-throw HTTP exceptions directly (e.g. rate limit, validation)
        # Clear idempotency lock so user can retry on validation/rate-limit failures
        if idempotency_key:
            await idempotency_service.delete_key(idempotency_key)
        raise
    except Exception as exc:
        # Clear idempotency lock on general exceptions
        if idempotency_key:
            await idempotency_service.delete_key(idempotency_key)
        raise exc

@router.get(
    "/notifications/{id}",
    response_model=NotificationResponse,
    summary="Get status of a notification",
)
async def get_status(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    repo = NotificationRepository(db)
    notification = await repo.get_by_id(id)
    if not notification:
        raise HTTPException(
            status_code=404,
            detail=f"Notification with ID {id} not found."
        )
    return notification
