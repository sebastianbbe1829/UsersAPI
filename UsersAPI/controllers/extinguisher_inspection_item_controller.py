from sqlalchemy.orm import Session

from ..schemas.extinguisher_inspection_item import (
    ExtinguisherInspectionItemCreate,
    ExtinguisherInspectionItemUpdate,
)
from ..services.extinguisher_inspection_item_service import (
    create_inspection_item,
    delete_inspection_item,
    get_inspection_item,
    list_inspection_items,
    update_inspection_item,
)


def listar_items_revision(db: Session):
    return list_inspection_items(db)


def obtener_item_revision(item_id: int, db: Session):
    return get_inspection_item(item_id, db)


def crear_item_revision(datos: ExtinguisherInspectionItemCreate, db: Session):
    return create_inspection_item(datos, db)


def actualizar_item_revision(
    item_id: int,
    datos: ExtinguisherInspectionItemUpdate,
    db: Session,
):
    return update_inspection_item(item_id, datos, db)


def desactivar_item_revision(item_id: int, db: Session):
    return delete_inspection_item(item_id, db)
