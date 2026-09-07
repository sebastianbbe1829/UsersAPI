from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from UsersAPI.domains.core.models import GlobalUserDB, UserTenantDB

from ..models import ClientComplianceOverrideDB
from ..repositories.client_repository import ClientRepository
from ..schemas.compliance_override import ClientComplianceOverrideRequest


def override_client_compliance(
    client_id: UUID,
    data: ClientComplianceOverrideRequest,
    db: Session,
    tenant_id: int,
    current_user: UserTenantDB | GlobalUserDB,
) -> ClientComplianceOverrideDB:
    client = ClientRepository(db).get_by_id(client_id, tenant_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if client.status != "BLOCKED" and not client.is_listed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El cliente no tiene una restricción de compliance activa",
        )

    latest_screening = max(client.screenings, key=lambda item: item.requested_at, default=None)
    now = datetime.now(UTC)
    override = ClientComplianceOverrideDB(
        tenant_id=tenant_id,
        client_id=client.id,
        screening_id=latest_screening.id if latest_screening else None,
        requested_by=current_user.id,
        requested_by_email=current_user.email,
        reason=data.reason.strip(),
        created_at=now,
    )
    db.add(override)

    # Keep the original MATCH/listing history intact. The override is an
    # auditable exception and the only supported way to release BLOCKED.
    client.status = "ACTIVE"
    client.updated_at = now
    client.updated_by = current_user.email
    db.add(client)
    db.flush()
    return override
