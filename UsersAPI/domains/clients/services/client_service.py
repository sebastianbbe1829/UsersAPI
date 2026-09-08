from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import ClientDB, IdentificationTypeDB
from ..repositories.client_repository import ClientRepository
from ..schemas.client import ClientCreate, ClientUpdate
from .screening_service import screen_client


def _normalizar_texto(valor: str | None) -> str:
    if not valor:
        return ""
    return " ".join(valor.strip().upper().split())


def _full_name(data: ClientCreate | ClientUpdate | ClientDB) -> str:
    if data.person_type == "JURIDICA":
        return _normalizar_texto(data.business_name)
    parts = [
        _normalizar_texto(data.first_name),
        _normalizar_texto(data.middle_name),
        _normalizar_texto(data.last_name),
        _normalizar_texto(data.second_last_name),
    ]
    return " ".join(part for part in parts if part)


def _validate_identity_data(db: Session, identification_type_id: int, person_type: str, full_name: str) -> None:
    _validate_identification_type(db, identification_type_id, person_type)
    if not full_name:
        detail = (
            "Natural person requires first_name and last_name"
            if person_type == "NATURAL"
            else "Legal person requires business_name"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _validate_identification_type(db: Session, identification_type_id: int, person_type: str) -> IdentificationTypeDB:
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


def _actor_name(current_user: object | None) -> str:
    return (
        getattr(current_user, "email", None)
        or getattr(current_user, "username", None)
        or "system"
    )


def create_client(data: ClientCreate, db: Session, tenant_id: int, current_user: object) -> ClientDB:
    if data.status == "BLOCKED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="BLOCKED is a system-managed compliance status",
        )
    full_name = _full_name(data)
    _validate_identity_data(db, data.identification_type_id, data.person_type, full_name)
    repository = ClientRepository(db)
    if repository.get_by_identification(data.identification_type_id, data.identification_number, tenant_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Client identification already exists in this tenant",
        )
    now = datetime.now(UTC)
    created_by = _actor_name(current_user)
    consent_at = data.consent_at if data.consent_given else None
    if data.consent_given and consent_at is None:
        consent_at = now
    datos = data.model_dump(exclude={"consent_at"})
    datos.update(
        {
            "first_name": _normalizar_texto(data.first_name),
            "middle_name": _normalizar_texto(data.middle_name),
            "last_name": _normalizar_texto(data.last_name),
            "second_last_name": _normalizar_texto(data.second_last_name),
            "business_name": _normalizar_texto(data.business_name),
            "email": _normalizar_texto(data.email) or None,
            "address": _normalizar_texto(data.address),
            "consent_source": _normalizar_texto(data.consent_source),
        }
    )
    client = ClientDB(
        tenant_id=tenant_id,
        full_name=full_name,
        created_at=now,
        created_by=created_by,
        consent_at=consent_at,
        **datos,
    )
    client = repository.add(client)
    screen_client(client, db)
    return client


def list_clients(db: Session, tenant_id: int, limit: int | None = None, offset: int = 0, search: str | None = None) -> list[ClientDB]:
    return ClientRepository(db).get_all(tenant_id, limit=limit, offset=offset, search=search)


def get_client(client_id: UUID, db: Session, tenant_id: int) -> ClientDB:
    client = ClientRepository(db).get_by_id(client_id, tenant_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


def update_client(client_id: UUID, data: ClientUpdate, db: Session, tenant_id: int, current_user: object) -> ClientDB:
    repository = ClientRepository(db)
    client = get_client(client_id, db, tenant_id)
    changes = data.model_dump(exclude_unset=True)

    if "status" in changes:
        requested_status = changes["status"]
        if requested_status == "BLOCKED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="BLOCKED is a system-managed compliance status",
            )
        if client.status == "BLOCKED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A blocked client can only be reactivated through the "
                    "compliance override flow"
                ),
            )
        if requested_status == "ACTIVE" and (client.compliance_status == "MATCH" or client.is_listed):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A client with an active compliance restriction can only "
                    "be reactivated through the compliance override flow"
                ),
            )

    identity_fields = {
        "identification_type_id",
        "identification_number",
        "person_type",
        "first_name",
        "middle_name",
        "last_name",
        "second_last_name",
        "business_name",
    }
    identity_changed = bool(identity_fields.intersection(changes))
    original_values = {field: getattr(client, field) for field in identity_fields}

    for field, value in changes.items():
        setattr(client, field, value)
    client.first_name = _normalizar_texto(client.first_name)
    client.middle_name = _normalizar_texto(client.middle_name)
    client.last_name = _normalizar_texto(client.last_name)
    client.second_last_name = _normalizar_texto(client.second_last_name)
    client.business_name = _normalizar_texto(client.business_name)
    client.email = _normalizar_texto(client.email) or None
    client.address = _normalizar_texto(client.address)
    client.consent_source = _normalizar_texto(client.consent_source)

    full_name = _full_name(client)
    _validate_identity_data(db, client.identification_type_id, client.person_type, full_name)
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
    client.updated_at = datetime.now(UTC)
    client.updated_by = _actor_name(current_user)
    if client.consent_given and client.consent_at is None:
        client.consent_at = client.updated_at
    elif not client.consent_given:
        client.consent_at = None
    client = repository.update(client)
    if identity_changed and any(original_values[field] != getattr(client, field) for field in identity_fields):
        screen_client(client, db)
    return client


def delete_client(client_id: UUID, db: Session, tenant_id: int, current_user: object | None = None) -> None:
    client = get_client(client_id, db, tenant_id)
    client.status = "INACTIVE"
    client.updated_at = datetime.now(UTC)
    client.updated_by = _actor_name(current_user)
    ClientRepository(db).update(client)
