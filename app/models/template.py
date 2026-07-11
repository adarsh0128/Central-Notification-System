import uuid
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class Template(Base, TimestampMixin):
    __tablename__ = "templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="The unique name identifier for the template (e.g. 'welcome_email').",
    )
    subject: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Optional subject line for channels like EMAIL.",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Template body containing {{variables}}.",
    )
