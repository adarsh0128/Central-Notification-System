import asyncio
import logging
import uuid
from typing import Any
from celery.exceptions import Retry

from app.workers.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.repositories.notification import NotificationRepository
from app.repositories.template import TemplateRepository
from app.services.template import TemplateService
from app.providers import EmailProvider, SMSProvider, PushProvider, ProviderError

# Setup Logger
logger = logging.getLogger(__name__)

def run_async(coro: Any) -> Any:
    """Helper to run async coroutines in a synchronous thread (like Celery worker thread)."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

@celery_app.task(bind=True, max_retries=3, acks_late=True)
def send_notification_delivery(self: Any, delivery_id_str: str) -> None:
    """Background task to deliver a specific notification channel.
    
    Uses exponential backoff retries:
      - 0th retry: countdown = 4^0 = 1s
      - 1st retry: countdown = 4^1 = 4s
      - 2nd retry: countdown = 4^2 = 16s
    """
    delivery_id = uuid.UUID(delivery_id_str)
    retry_count = self.request.retries
    countdown = 4 ** retry_count

    async def _execute() -> None:
        async with AsyncSessionLocal() as db:
            repo = NotificationRepository(db)
            template_repo = TemplateRepository(db)
            template_service = TemplateService()

            delivery = await repo.get_delivery_by_id(delivery_id)
            if not delivery:
                logger.error(f"Delivery record {delivery_id_str} not found in database.")
                return

            # Check if delivery has already completed to avoid duplicate execution
            if delivery.status in ("SENT", "DELIVERED", "FAILED"):
                logger.info(f"Delivery {delivery_id_str} already in terminal state: {delivery.status}")
                return

            notification = await repo.get_by_id(delivery.notification_id)
            if not notification:
                logger.error(f"Notification record {delivery.notification_id} not found in database.")
                return

            # Load Template
            template = await template_repo.get_by_id(notification.template_id) if notification.template_id else None
            if not template:
                logger.error(f"Template {notification.template_id} not found for notification {notification.id}")
                await repo.update_delivery_status(
                    delivery_id, "FAILED", error_message="Associated template was deleted or not found."
                )
                return

            # Render Template
            try:
                subject, content = template_service.render_subject_and_body(
                    template.content,
                    template.subject,
                    notification.template_variables or {},
                )
            except Exception as err:
                logger.error(f"Template rendering failed for template {template.name}: {str(err)}")
                await repo.update_delivery_status(
                    delivery_id, "FAILED", error_message=f"Template compilation error: {str(err)}"
                )
                return

            # Initialize mock clients based on target channel
            if delivery.channel == "EMAIL":
                provider = EmailProvider()
                target = f"{notification.user_id}@example.com"
            elif delivery.channel == "SMS":
                provider = SMSProvider()
                target = "+15555555555"
            elif delivery.channel == "PUSH":
                provider = PushProvider()
                target = f"push_token_{notification.user_id}"
            else:
                logger.error(f"Unsupported delivery channel: {delivery.channel}")
                await repo.update_delivery_status(
                    delivery_id, "FAILED", error_message=f"Unsupported channel: {delivery.channel}"
                )
                return

            # Inject trace contexts into logging
            from app.core.logging import (
                request_id_ctx,
                user_id_ctx,
                notification_id_ctx,
                channel_ctx,
                status_ctx,
            )
            user_id_ctx.set(notification.user_id)
            notification_id_ctx.set(str(notification.id))
            channel_ctx.set(delivery.channel)
            status_ctx.set(delivery.status)

            try:
                # Transition PENDING -> SENT
                await repo.update_delivery_status(delivery_id, "SENT")

                # Invoke delivery provider
                await provider.send(target=target, content=content, subject=subject)

                # Transition SENT -> DELIVERED
                await repo.update_delivery_status(delivery_id, "DELIVERED")

            except ProviderError as exc:
                logger.warning(
                    f"Provider failed to deliver. Delivery: {delivery_id_str}. Retry: {retry_count}",
                    extra={"error": str(exc)},
                )

                if retry_count >= self.max_retries:
                    # Max retries exhausted: Transition -> FAILED
                    await repo.update_delivery_status(
                        delivery_id,
                        "FAILED",
                        error_message=f"Delivery failed after max retries: {str(exc)}",
                        increment_retry=True,
                    )
                    raise exc
                else:
                    # Update status back to PENDING and increment retry count
                    await repo.update_delivery_status(
                        delivery_id,
                        "PENDING",
                        error_message=f"Provider transient error: {str(exc)}",
                        increment_retry=True,
                    )
                    # Trigger Celery task retry
                    self.retry(exc=exc, countdown=countdown)

            except Exception as exc:
                # Fatal/unexpected error
                logger.exception(f"Unexpected fatal error executing delivery {delivery_id_str}")
                await repo.update_delivery_status(
                    delivery_id, "FAILED", error_message=f"Fatal exception: {str(exc)}"
                )
                raise exc

    try:
        run_async(_execute())
    except Retry:
        raise  # Must propagate Celery's Retry exception so Celery handles the retry
    except Exception as err:
        logger.error(f"Celery task wrapper caught exception: {str(err)}")
        raise err

@celery_app.task
def reconcile_pending_deliveries() -> None:
    """Periodic reconciliation task running via Celery Beat.
    
    Identifies delivery jobs stuck in PENDING status for more than 5 minutes,
    and re-queues them to prevent system failures from losing messages.
    """
    async def _execute() -> None:
        async with AsyncSessionLocal() as db:
            repo = NotificationRepository(db)
            # Find pending deliveries older than 5 minutes (300 seconds)
            stuck_deliveries = await repo.get_pending_deliveries(max_age_seconds=300)

            if not stuck_deliveries:
                return

            logger.info(f"Reconciliation Job: Found {len(stuck_deliveries)} stuck pending deliveries.")

            for delivery in stuck_deliveries:
                notification = await repo.get_by_id(delivery.notification_id)
                priority = notification.priority if notification else "NORMAL"
                
                # Determine queue name based on priority
                queue_name = priority.lower()
                if queue_name == "normal":
                    queue_name = "default"

                logger.info(
                    f"Re-queuing stuck delivery {delivery.id} to queue '{queue_name}'",
                    extra={"delivery_id": str(delivery.id), "queue": queue_name}
                )

                # Re-enqueue delivery
                send_notification_delivery.apply_async(
                    args=[str(delivery.id)],
                    queue=queue_name
                )
                
    run_async(_execute())
