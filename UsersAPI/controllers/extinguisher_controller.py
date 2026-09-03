from sqlalchemy.orm import Session

from ..models import UserTenantDB
from ..schemas import ExtinguisherCreate, ExtinguisherUpdate
from ..services.extinguisher_export_service import export_extinguishers
from ..services.extinguisher_service import (
    create_extinguisher,
    delete_extinguisher,
    get_extinguisher,
    list_extinguishers,
    search_extinguishers,
    update_extinguisher,
)


def crear_extintor(datos: ExtinguisherCreate, db: Session, user_tenant: UserTenantDB):
    return create_extinguisher(datos, db, user_tenant)


def listar_extintores(db: Session, tenant_id: int, include_inactive: bool = False):
    return list_extinguishers(db, tenant_id, include_inactive)


def buscar_extintores(db: Session, tenant_id: int, search: str = "", limit: int = 20):
    return search_extinguishers(db, tenant_id, search, limit)


def obtener_extintor(extinguisher_id: int, db: Session, tenant_id: int):
    return get_extinguisher(extinguisher_id, db, tenant_id)


def actualizar_extintor(
    extinguisher_id: int,
    datos: ExtinguisherUpdate,
    db: Session,
    user_tenant: UserTenantDB,
):
    return update_extinguisher(extinguisher_id, datos, db, user_tenant)


def eliminar_extintor(extinguisher_id: int, db: Session, user_tenant: UserTenantDB):
    return delete_extinguisher(extinguisher_id, db, user_tenant)


def exportar_extintores(
    db: Session,
    current_user: UserTenantDB,
    user_tenant: UserTenantDB,
):
    return export_extinguishers(db, current_user, user_tenant.tenant_id)
