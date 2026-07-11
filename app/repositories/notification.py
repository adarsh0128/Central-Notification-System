import uuid
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.notification import (
    Notification,
    NotificationDelivery,
    NotificationStatusLog,
)
from app.repositories.base import BaseRepository

class NotificationRepository(BaseRepository):
    async def create_notification(
        self,
        user_id: str,
        template_id: uuid.UUID | None,
        template_variables: dict[str, Any] | None,
        priority: str,
        idempotency_key: str | None = None,
    ) -> Notification:
        """Saves a notification metadata row."""
        notification = Notification(
            user_id=user_id,
            template_id=template_id,
            template_variables=template_variables,
            priority=priority,
            idempotency_key=idempotency_key,
        )
        self.db.add(notification)
        await self.db.flush()  # Generate ID without committing transaction
        return notification

    async def create_delivery(
        self, notification_id: uuid.UUID, channel: str, status: str = "PENDING"
    ) -> NotificationDelivery:
        """Saves an initial notification delivery row and logs the transition."""
        delivery = NotificationDelivery(
            notification_id=notification_id,
            channel=channel,
            status=status,
        )
        self.db.add(delivery)
        await self.db.flush()

        log_entry = NotificationStatusLog(
            delivery_id=delivery.id,
            from_status="NONE",
            to_status=status,
        )
        self.db.add(log_entry)
        await self.db.flush()
        return delivery

    async def update_delivery_status(
        self,
        delivery_id: uuid.UUID,
        to_status: str,
        error_message: str | None = None,
        increment_retry: bool = False,
    ) -> NotificationDelivery | None:
        """Atomic state machine transition updater.
        
        Updates delivery status, increments retry counts if specified,
        adds a status transition log entry, and commits the transaction.
        """
        stmt = select(NotificationDelivery).where(NotificationDelivery.id == delivery_id)
        result = await self.db.execute(stmt)
        delivery = result.scalar_one_or_none()
        if not delivery:
            return None

        from_status = delivery.status
        delivery.status = to_status
        if error_message is not None:
            delivery.error_message = error_message
        if increment_retry:
            delivery.retry_count += 1

        log_entry = NotificationStatusLog(
            delivery_id=delivery_id,
            from_status=from_status,
            to_status=to_status,
        )
        self.db.add(log_entry)
        self.db.add(delivery)
        await self.db.commit()
        await self.db.refresh(delivery)
        return delivery

    async def get_by_id(self, notification_id: uuid.UUID) -> Notification | None:
        """Fetches a single notification and pre-loads its deliveries."""
        stmt = (
            select(Notification)
            .options(selectinload(Notification.deliveries))
            .where(Notification.id == notification_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_delivery_by_id(self, delivery_id: uuid.UUID) -> NotificationDelivery | None:
        """Fetches a single notification delivery record by its ID."""
        stmt = select(NotificationDelivery).where(NotificationDelivery.id == delivery_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_history(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> list[Notification]:
        """Fetches user notification history with pagination."""
        stmt = (
            select(Notification)
            .options(selectinload(Notification.deliveries))
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_deliveries(self, max_age_seconds: int = 300) -> list[NotificationDelivery]:
        """Fetches delivery rows that are still stuck in PENDING status for too long.
        
        Useful for reconciliation scripts.
        """
        import datetime
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=max_age_seconds)
        stmt = (
            select(NotificationDelivery)
            .where(NotificationDelivery.status == "PENDING")
            .where(NotificationDelivery.created_at < cutoff)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def commit(self) -> None:
        """Public commit wrapper for bulk operations."""
        await self.db.commit()
