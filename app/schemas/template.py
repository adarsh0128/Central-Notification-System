import uuid
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class TemplateCreate(BaseModel):
    name: str = Field(..., description="Unique name identifier for the template.")
    subject: str | None = Field(default=None, description="Optional subject line for channels like email.")
    content: str = Field(..., description="Template body containing {{variable}} placeholders.")

class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    name: str
    subject: str | None
    content: str
    created_at: datetime = Field(..., serialization_alias="createdAt")
    updated_at: datetime = Field(..., serialization_alias="updatedAt")
