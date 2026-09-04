from sqlalchemy.orm import Session

from ..services.catalog_service import (
    list_cities,
    list_countries,
    list_departments,
    list_identification_types,
)


def listar_tipos_identificacion(db: Session):
    return list_identification_types(db)


def listar_paises(db: Session):
    return list_countries(db)


def listar_departamentos(db: Session, country_id: int | None = None):
    return list_departments(db, country_id)


def listar_ciudades(db: Session, department_id: int | None = None):
    return list_cities(db, department_id)
