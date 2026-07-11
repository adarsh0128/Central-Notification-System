import uuid
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, ConfigDict

class PriorityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"

class ChannelEnum(str, Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"

class NotificationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(
        ...,
        validation_alias="userId",
        serialization_alias="userId",
        description="The target user identifier.",
    )
    channels: list[ChannelEnum] | None = Field(
        default=None,
        description="Optional list of target channels. If not provided, defaults to all channels the user has opted into.",
    )
    template_name: str = Field(
        ...,
        validation_alias="templateName",
        serialization_alias="templateName",
        description="The template name used to compile the message.",
    )
    variables: dict[str, Any] = Field(
        default_factory=dict,
        description="The key-value pairs used for template variable substitution.",
    )
    priority: PriorityEnum = Field(
        default=PriorityEnum.NORMAL,
        description="The priority level of the notification.",
    )

class NotificationDeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    channel: str
    status: str
    retry_count: int = Field(..., serialization_alias="retryCount")
    error_message: str | None = Field(..., serialization_alias="errorMessage")
    created_at: datetime = Field(..., serialization_alias="createdAt")
    updated_at: datetime = Field(..., serialization_alias="updatedAt")

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    user_id: str = Field(..., serialization_alias="userId")
    template_id: uuid.UUID | None = Field(..., serialization_alias="templateId")
    template_variables: dict[str, Any] | None = Field(..., serialization_alias="templateVariables")
    priority: str
    deliveries: list[NotificationDeliveryResponse]
    created_at: datetime = Field(..., serialization_alias="createdAt")
    updated_at: datetime = Field(..., serialization_alias="updatedAt")
