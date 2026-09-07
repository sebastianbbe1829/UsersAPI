from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ClientScreeningRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: int
    client_id: UUID
    provider: str
    status: str
    risk_level: str | None
    matched: bool
    requested_at: datetime
    completed_at: datetime | None
    response: dict | None
    error_message: str | None
