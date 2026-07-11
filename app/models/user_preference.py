from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class UserPreference(Base, TimestampMixin):
    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        index=True,
        comment="The unique user identifier.",
    )
    email_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether email channel is enabled.",
    )
    sms_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether SMS channel is enabled.",
    )
    push_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether push/in-app channel is enabled.",
    )
