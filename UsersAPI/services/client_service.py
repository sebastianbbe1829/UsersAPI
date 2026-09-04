from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..logging_config import logger
from ..models import ClientDB, GlobalUserDB, UserTenantDB
from ..repositories.client_repository import ClientRepository
from ..schemas import ClientCreate, ClientUpdate


def _normalize_create(data: ClientCreate) -> dict:
    values = data.model_dump()
    for field in ("client_type", "id_type", "id_number", "country_code"):
        values[field] = values[field].strip().upper()
    for field in ("first_name", "middle_name", "last_name", "second_last_name", "legal_name", "trade_name", "phone", "address"):
        if values[field] is not None:
            values[field] = values[field].strip() or None
    if values["email"] is not None:
        values["email"] = str(values["email"]).strip().lower()
    return values


def create_client(
    data: ClientCreate,
    db: Session,
    current_user: UserTenantDB | GlobalUserDB,
    tenant_id: int,
) -> ClientDB:
    values = _normalize_create(data)
    repo = ClientRepository(db)

    if repo.get_by_identification_and_tenant(values["id_type"], values["id_number"], tenant_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El cliente ya existe en este tenant con esa identificación",
        )

    created_by = getattr(current_user, "email", None) or getattr(current_user, "dni", None) or "SYSTEM"
    client = ClientDB(tenant_id=tenant_id, created_by=created_by, **values)

    try:
        repo.add(client)
        db.refresh(client)
    except IntegrityError as exc:
        db.rollback()
        logger.exception("Error de integridad creando cliente")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No fue posible crear el cliente",
        ) from exc
    return client


def list_clients(db: Session, tenant_id: int, include_inactive: bool = False):
    return ClientRepository(db).get_all_by_tenant(tenant_id, include_inactive)


def search_clients(db: Session, tenant_id: int, search: str = "", limit: int = 20):
    return ClientRepository(db).search_by_tenant(tenant_id, search, limit)


def get_client(client_uuid: UUID, db: Session, tenant_id: int):
    client = ClientRepository(db).get_by_uuid_and_tenant(client_uuid, tenant_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client


def update_client(
    client_uuid: UUID,
    data: ClientUpdate,
    db: Session,
    current_user: UserTenantDB | GlobalUserDB,
    tenant_id: int,
):
    repo = ClientRepository(db)
    client = repo.get_by_uuid_and_tenant(client_uuid, tenant_id, include_inactive=True)
    if client is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    changes = data.model_dump(exclude_unset=True)
    for field in ("client_type", "id_type", "country_code", "status"):
        if field in changes and changes[field] is not None:
            changes[field] = changes[field].strip().upper()
    for field in ("first_name", "middle_name", "last_name", "second_last_name", "legal_name", "trade_name", "phone", "address"):
        if field in changes and changes[field] is not None:
            changes[field] = changes[field].strip() or None
    if "id_number" in changes and changes["id_number"] is not None:
        changes["id_number"] = changes["id_number"].strip().upper()
    if "email" in changes and changes["email"] is not None:
        changes["email"] = str(changes["email"]).strip().lower()

    next_type = changes.get("client_type", client.client_type)
    next_first = changes.get("first_name", client.first_name)
    next_last = changes.get("last_name", client.last_name)
    next_legal = changes.get("legal_name", client.legal_name)
    if next_type == "PERSON" and (not next_first or not next_last):
        raise HTTPException(status_code=400, detail="PERSON requiere first_name y last_name")
    if next_type == "COMPANY" and not next_legal:
        raise HTTPException(status_code=400, detail="COMPANY requiere legal_name")
    if next_type not in {"PERSON", "COMPANY"}:
        raise HTTPException(status_code=400, detail="client_type debe ser PERSON o COMPANY")

    if "id_type" in changes or "id_number" in changes:
        id_type = changes.get("id_type", client.id_type)
        id_number = changes.get("id_number", client.id_number)
        existing = repo.get_by_identification_and_tenant(id_type, id_number, tenant_id)
        if existing is not None and existing.uuid != client.uuid:
            raise HTTPException(status_code=409, detail="La identificación ya existe en este tenant")

    if "consent_contact" in changes:
        if changes["consent_contact"]:
            changes.setdefault("consent_contact_at", datetime.now())
        else:
            changes["consent_contact_at"] = None

    updated_by = getattr(current_user, "email", None) or getattr(current_user, "dni", None) or "SYSTEM"
    for field, value in changes.items():
        setattr(client, field, value)
    client.updated_by = updated_by
    client.updated_at = datetime.now()

    repo.update(client)
    db.refresh(client)
    return client


def delete_client(client_uuid: UUID, db: Session, current_user: UserTenantDB | GlobalUserDB, tenant_id: int):
    client = ClientRepository(db).get_by_uuid_and_tenant(client_uuid, tenant_id, include_inactive=True)
    if client is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    client.status = "INACTIVE"
    client.updated_by = getattr(current_user, "email", None) or getattr(current_user, "dni", None) or "SYSTEM"
    client.updated_at = datetime.now()
    return {"message": "Cliente desactivado correctamente", "uuid": client.uuid}
