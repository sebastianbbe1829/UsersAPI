from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..logging_config import logger
from ..models import ExtinguisherDB, ExtinguisherTypeDB, UserTenantDB
from ..repositories.extinguisher_repository import ExtinguisherRepository
from ..schemas import ExtinguisherCreate, ExtinguisherUpdate


def _normalize_code(code: str) -> str:
    return code.strip().upper()


def _validate_type(type_id: int, db: Session) -> ExtinguisherTypeDB:
    item = db.query(ExtinguisherTypeDB).filter(
        ExtinguisherTypeDB.id == type_id,
        ExtinguisherTypeDB.active.is_(True),
    ).first()
    if item is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de extintor no encontrado o inactivo")
    return item


def create_extinguisher(datos: ExtinguisherCreate, db: Session, user_tenant: UserTenantDB):
    tenant_id = user_tenant.tenant_id
    repo = ExtinguisherRepository(db)
    code = _normalize_code(datos.code)
    if not code:
        raise HTTPException(status_code=400, detail="El código del extintor es obligatorio")
    if repo.get_by_code_and_tenant(code, tenant_id, include_inactive=True):
        raise HTTPException(status_code=409, detail="El código del extintor ya existe en este tenant")

    _validate_type(datos.extinguisher_type_id, db)
    extinguisher = ExtinguisherDB(
        tenant_id=tenant_id, code=code, extinguisher_type_id=datos.extinguisher_type_id,
        capacity=datos.capacity, location=datos.location,
        last_recharge_date=datos.last_recharge_date, next_recharge_date=datos.next_recharge_date,
        last_hydrostatic_test_date=datos.last_hydrostatic_test_date,
        next_hydrostatic_test_date=datos.next_hydrostatic_test_date,
        status=datos.status.strip().upper(), is_stock=datos.is_stock, active=True,
    )
    try:
        repo.add(extinguisher)
        db.refresh(extinguisher)
    except IntegrityError as exc:
        db.rollback()
        logger.exception("Error de integridad creando extintor")
        raise HTTPException(status_code=409, detail="No fue posible crear el extintor") from exc
    return extinguisher


def list_extinguishers(db: Session, tenant_id: int, include_inactive: bool = False):
    return ExtinguisherRepository(db).get_all_by_tenant(tenant_id, include_inactive)


def search_extinguishers(db: Session, tenant_id: int, search: str = "", limit: int = 20):
    return ExtinguisherRepository(db).search_by_tenant(tenant_id, search, limit)


def get_extinguisher(extinguisher_id: int, db: Session, tenant_id: int):
    extinguisher = ExtinguisherRepository(db).get_by_id_and_tenant(extinguisher_id, tenant_id)
    if extinguisher is None:
        raise HTTPException(status_code=404, detail="Extintor no encontrado")
    return extinguisher


def update_extinguisher(extinguisher_id: int, datos: ExtinguisherUpdate, db: Session, user_tenant: UserTenantDB):
    tenant_id = user_tenant.tenant_id
    repo = ExtinguisherRepository(db)
    extinguisher = repo.get_by_id_and_tenant(extinguisher_id, tenant_id, include_inactive=True)
    if extinguisher is None:
        raise HTTPException(status_code=404, detail="Extintor no encontrado")

    cambios = datos.model_dump(exclude_unset=True)
    if "code" in cambios:
        code = _normalize_code(cambios["code"])
        existente = repo.get_by_code_and_tenant(code, tenant_id, include_inactive=True)
        if existente is not None and existente.id != extinguisher.id:
            raise HTTPException(status_code=409, detail="El código del extintor ya existe en este tenant")
        cambios["code"] = code
    if "extinguisher_type_id" in cambios:
        _validate_type(cambios["extinguisher_type_id"], db)
    if "status" in cambios:
        cambios["status"] = cambios["status"].strip().upper()

    for campo, valor in cambios.items():
        setattr(extinguisher, campo, valor)
    extinguisher.updated_at = datetime.now()
    repo.update(extinguisher)
    db.refresh(extinguisher)
    return extinguisher


def delete_extinguisher(extinguisher_id: int, db: Session, user_tenant: UserTenantDB):
    extinguisher = ExtinguisherRepository(db).get_by_id_and_tenant(extinguisher_id, user_tenant.tenant_id, include_inactive=True)
    if extinguisher is None:
        raise HTTPException(status_code=404, detail="Extintor no encontrado")
    extinguisher.active = False
    extinguisher.updated_at = datetime.now()
    return {"message": "Extintor desactivado correctamente", "id": extinguisher.id}
