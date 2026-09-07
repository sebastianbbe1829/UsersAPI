from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ClientComplianceOverrideRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=2000)


class ClientComplianceOverrideRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: int
    client_id: UUID
    screening_id: UUID | None
    requested_by: int
    requested_by_email: str
    reason: str
    created_at: datetime
