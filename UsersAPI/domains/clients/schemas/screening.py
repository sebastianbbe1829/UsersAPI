from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ClientScreeningRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    identification_number: str
    full_name: str
    person_type: str
    provider: str
    status: str
    risk_level: str | None
    matched: bool
    list_type: str | None
    requested_at: datetime
    completed_at: datetime | None
    response: dict | None
    error_message: str | None
