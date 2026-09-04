from sqlalchemy.orm import Session

from ..schemas.catalog import (
    CityCreate,
    CityUpdate,
    CountryCreate,
    CountryUpdate,
    DepartmentCreate,
    DepartmentUpdate,
    IdentificationTypeCreate,
    IdentificationTypeUpdate,
)
from ..services.catalog_service import (
    create_city,
    create_country,
    create_department,
    create_identification_type,
    delete_city,
    delete_country,
    delete_department,
    delete_identification_type,
    get_city,
    get_country,
    get_department,
    get_identification_type,
    list_cities,
    list_countries,
    list_departments,
    list_identification_types,
    update_city,
    update_country,
    update_department,
    update_identification_type,
)


def listar_tipos_identificacion(db: Session, include_inactive: bool = False):
    return list_identification_types(db, include_inactive)


def obtener_tipo_identificacion(db: Session, item_id: int):
    return get_identification_type(db, item_id)


def crear_tipo_identificacion(db: Session, data: IdentificationTypeCreate):
    return create_identification_type(db, data)


def actualizar_tipo_identificacion(db: Session, item_id: int, data: IdentificationTypeUpdate):
    return update_identification_type(db, item_id, data)


def eliminar_tipo_identificacion(db: Session, item_id: int):
    delete_identification_type(db, item_id)


def listar_paises(db: Session, include_inactive: bool = False):
    return list_countries(db, include_inactive)


def obtener_pais(db: Session, item_id: int):
    return get_country(db, item_id)


def crear_pais(db: Session, data: CountryCreate):
    return create_country(db, data)


def actualizar_pais(db: Session, item_id: int, data: CountryUpdate):
    return update_country(db, item_id, data)


def eliminar_pais(db: Session, item_id: int):
    delete_country(db, item_id)


def listar_departamentos(db: Session, country_id: int | None = None, include_inactive: bool = False):
    return list_departments(db, country_id, include_inactive)


def obtener_departamento(db: Session, item_id: int):
    return get_department(db, item_id)


def crear_departamento(db: Session, data: DepartmentCreate):
    return create_department(db, data)


def actualizar_departamento(db: Session, item_id: int, data: DepartmentUpdate):
    return update_department(db, item_id, data)


def eliminar_departamento(db: Session, item_id: int):
    delete_department(db, item_id)


def listar_ciudades(db: Session, department_id: int | None = None, include_inactive: bool = False):
    return list_cities(db, department_id, include_inactive)


def obtener_ciudad(db: Session, item_id: int):
    return get_city(db, item_id)


def crear_ciudad(db: Session, data: CityCreate):
    return create_city(db, data)


def actualizar_ciudad(db: Session, item_id: int, data: CityUpdate):
    return update_city(db, item_id, data)


def eliminar_ciudad(db: Session, item_id: int):
    delete_city(db, item_id)
