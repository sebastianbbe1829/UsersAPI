from sqlalchemy.orm import Session

from ..schemas import ExtinguisherTypeCreate
from ..services.extinguisher_type_service import create_extinguisher_type, list_extinguisher_types


def listar_tipos_extintor(db: Session):
    return list_extinguisher_types(db)


def crear_tipo_extintor(datos: ExtinguisherTypeCreate, db: Session):
    return create_extinguisher_type(datos, db)
