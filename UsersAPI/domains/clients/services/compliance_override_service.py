from datetime import UTC, datetime
from uuid import UUID

import pyotp
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from UsersAPI.domains.core.models import GlobalUserDB
from UsersAPI.domains.core.services.global_auth_service import _decrypt_mfa_secret

from ..models import ClientComplianceOverrideDB
from ..repositories.client_repository import ClientRepository
from ..schemas.compliance_override import ClientComplianceOverrideRequest


def override_client_compliance(
    client_id: UUID,
    data: ClientComplianceOverrideRequest,
    db: Session,
    tenant_id: int,
    current_user: GlobalUserDB,
) -> ClientComplianceOverrideDB:
    if not isinstance(current_user, GlobalUserDB) or not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La liberación de una restricción requiere una sesión SUPER",
        )
    if not current_user.mfa_enabled or not current_user.mfa_secret_encrypted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario SUPER no tiene MFA configurado",
        )

    secret = _decrypt_mfa_secret(current_user.mfa_secret_encrypted)
    if not pyotp.TOTP(secret).verify(data.otp, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código MFA inválido",
        )

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
        mfa_verified_at=now,
        created_at=now,
    )
    db.add(override)

    # The original screening remains MATCH/listed. The override is an
    # auditable exception and is the only supported way to release BLOCKED.
    client.status = "ACTIVE"
    client.updated_at = now
    client.updated_by = current_user.email
    db.add(client)
    db.flush()
    return override
