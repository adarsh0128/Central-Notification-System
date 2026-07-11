import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import String, ForeignKey, Integer, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    template_variables: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    priority: Mapped[str] = mapped_column(
        String(50),
        default="NORMAL",
        nullable=False,  # CRITICAL, HIGH, NORMAL, LOW
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=True,
    )

    # Relationships
    deliveries: Mapped[list["NotificationDelivery"]] = relationship(
        "NotificationDelivery",
        back_populates="notification",
        cascade="all, delete-orphan",
    )
    template: Mapped["Template"] = relationship("Template")

class NotificationDelivery(Base, TimestampMixin):
    __tablename__ = "notification_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(
        String(50),
        nullable=False,  # EMAIL, SMS, PUSH
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,  # PENDING, SENT, DELIVERED, FAILED
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    notification: Mapped["Notification"] = relationship(
        "Notification",
        back_populates="deliveries",
    )
    status_logs: Mapped[list["NotificationStatusLog"]] = relationship(
        "NotificationStatusLog",
        back_populates="delivery",
        cascade="all, delete-orphan",
    )

class NotificationStatusLog(Base):
    __tablename__ = "notification_status_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    delivery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notification_deliveries.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    to_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    delivery: Mapped["NotificationDelivery"] = relationship(
        "NotificationDelivery",
        back_populates="status_logs",
    )
