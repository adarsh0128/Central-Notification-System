from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class UserPreferenceRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email_enabled: bool = Field(default=True, serialization_alias="emailEnabled", validation_alias="emailEnabled")
    sms_enabled: bool = Field(default=True, serialization_alias="smsEnabled", validation_alias="smsEnabled")
    push_enabled: bool = Field(default=True, serialization_alias="pushEnabled", validation_alias="pushEnabled")

class UserPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    user_id: str = Field(..., serialization_alias="userId", validation_alias="userId")
    email_enabled: bool = Field(..., serialization_alias="emailEnabled", validation_alias="emailEnabled")
    sms_enabled: bool = Field(..., serialization_alias="smsEnabled", validation_alias="smsEnabled")
    push_enabled: bool = Field(..., serialization_alias="pushEnabled", validation_alias="pushEnabled")
    created_at: datetime = Field(..., serialization_alias="createdAt", validation_alias="createdAt")
    updated_at: datetime = Field(..., serialization_alias="updatedAt", validation_alias="updatedAt")
