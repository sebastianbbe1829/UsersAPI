from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ScreeningSyncExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trigger_type: str
    triggered_by: int | None
    triggered_by_email: str | None
    status: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    total_sources: int | None
    successful_sources: int | None
    failed_sources: int | None
    result: dict | None
    error_message: str | None


class ScreeningSyncExecutionAccepted(BaseModel):
    id: UUID
    status: str
    message: str
