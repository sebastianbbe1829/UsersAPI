from sqlalchemy.orm import Session

from ..models import UserTenantDB
from ..schemas.extinguisher_inspection import ExtinguisherInspectionCreate
from ..services.extinguisher_inspection_service import (
    create_inspection,
    get_inspection,
    list_inspection_items,
    list_inspections,
)


def listar_items_revision(db: Session):
    return list_inspection_items(db)


def listar_revisiones(db: Session, tenant_id: int, extinguisher_id: int | None = None):
    return list_inspections(db, tenant_id, extinguisher_id)


def obtener_revision(inspection_id: int, db: Session, tenant_id: int):
    return get_inspection(inspection_id, db, tenant_id)


def crear_revision(
    extinguisher_id: int,
    datos: ExtinguisherInspectionCreate,
    db: Session,
    user_tenant: UserTenantDB,
):
    return create_inspection(extinguisher_id, datos, db, user_tenant)
