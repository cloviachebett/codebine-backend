import uuid
from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, Field


class AuditLogBase(BaseModel):
    user_id: Optional[uuid.UUID] = None
    action_type: str = Field(..., max_length=100)
    entity_type: str = Field(..., max_length=100)
    entity_id: Optional[str] = Field(None, max_length=64)
    execution_details: Optional[Dict[str, Any]] = None


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogResponse(AuditLogBase):
    log_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
