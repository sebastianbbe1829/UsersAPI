from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import ClientDB, IdentificationTypeDB
from ..repositories.client_repository import ClientRepository
from ..schemas.client import ClientCreate, ClientUpdate


def _full_name(data: ClientCreate | ClientUpdate | ClientDB) -> str:
    if data.person_type == "JURIDICA":
        return (data.business_name or "").strip()

    parts = [
        data.first_name,
        data.middle_name,
        data.last_name,
        data.second_last_name,
    ]
    return " ".join(part.strip() for part in parts if part and part.strip())


def _validate_identity_data(
    db: Session,
    identification_type_id: int,
    person_type: str,
    full_name: str,
) -> None:
    _validate_identification_type(db, identification_type_id, person_type)
    if not full_name:
        if person_type == "NATURAL":
            detail = "Natural person requires first_name and last_name"
        else:
            detail = "Legal person requires business_name"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


def _validate_identification_type(
    db: Session,
    identification_type_id: int,
    person_type: str,
) -> IdentificationTypeDB:
    identification_type = (
        db.query(IdentificationTypeDB)
        .filter(
            IdentificationTypeDB.id == identification_type_id,
            IdentificationTypeDB.active.is_(True),
        )
        .first()
    )
    if identification_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identification type not found or inactive",
        )
    if identification_type.person_type != person_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identification type is not valid for the person type",
        )
    return identification_type


def create_client(
    data: ClientCreate,
    db: Session,
    tenant_id: int,
    current_user: object,
) -> ClientDB:
    full_name = _full_name(data)
    _validate_identity_data(
        db,
        data.identification_type_id,
        data.person_type,
        full_name,
    )

    repository = ClientRepository(db)
    if repository.get_by_identification(
        data.identification_type_id,
        data.identification_number,
        tenant_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Client identification already exists in this tenant",
        )

    now = datetime.utcnow()
    created_by = getattr(current_user, "email", None) or getattr(current_user, "username", None) or "system"
    consent_at = data.consent_at if data.consent_given else None
    if data.consent_given and consent_at is None:
        consent_at = now

    client = ClientDB(
        tenant_id=tenant_id,
        full_name=full_name,
        created_at=now,
        created_by=created_by,
        consent_at=consent_at,
        **data.model_dump(exclude={"consent_at"}),
    )
    return repository.add(client)


def list_clients(db: Session, tenant_id: int) -> list[ClientDB]:
    return ClientRepository(db).get_all(tenant_id)


def get_client(client_id: UUID, db: Session, tenant_id: int) -> ClientDB:
    client = ClientRepository(db).get_by_id(client_id, tenant_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    return client


def update_client(
    client_id: UUID,
    data: ClientUpdate,
    db: Session,
    tenant_id: int,
    current_user: object,
) -> ClientDB:
    repository = ClientRepository(db)
    client = get_client(client_id, db, tenant_id)
    changes = data.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(client, field, value)

    full_name = _full_name(client)
    _validate_identity_data(
        db,
        client.identification_type_id,
        client.person_type,
        full_name,
    )

    if "identification_type_id" in changes or "identification_number" in changes:
        duplicate = repository.get_by_identification(
            client.identification_type_id,
            client.identification_number,
            tenant_id,
        )
        if duplicate is not None and duplicate.id != client.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Client identification already exists in this tenant",
            )

    client.full_name = full_name
    client.updated_at = datetime.utcnow()
    client.updated_by = (
        getattr(current_user, "email", None)
        or getattr(current_user, "username", None)
        or "system"
    )
    if client.consent_given and client.consent_at is None:
        client.consent_at = client.updated_at
    elif not client.consent_given:
        client.consent_at = None

    return repository.update(client)


def delete_client(client_id: UUID, db: Session, tenant_id: int) -> None:
    client = get_client(client_id, db, tenant_id)
    ClientRepository(db).delete(client)
