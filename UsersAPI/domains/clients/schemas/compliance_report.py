from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ClientRestrictedListReportRead(BaseModel):
    client_id: UUID
    identification_number: str
    full_name: str
    person_type: str
    status: str
    compliance_status: str
    list_type: str | None
    is_listed: bool
    client_created_at: datetime
    client_created_by: str
    screening_id: UUID | None
    screening_requested_at: datetime | None
    screening_completed_at: datetime | None
    screening_status: str | None
    screening_risk_level: str | None
    screening_matched: bool | None
    screening_error: str | None


class ClientComplianceOverrideHistoryRead(BaseModel):
    id: UUID
    client_id: UUID
    identification_number: str
    full_name: str
    screening_id: UUID | None
    requested_by: int
    requested_by_email: str
    reason: str
    created_at: datetime
