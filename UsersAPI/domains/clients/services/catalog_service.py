from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import CityDB, ClientDB, CountryDB, DepartmentDB, IdentificationTypeDB
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


def _not_found(detail: str):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _conflict(detail: str):
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _commit(db: Session):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        _conflict("El registro ya existe o está siendo utilizado por otros registros.")


def list_identification_types(
    db: Session,
    include_inactive: bool = False,
) -> list[IdentificationTypeDB]:
    query = db.query(IdentificationTypeDB)
    if not include_inactive:
        query = query.filter(IdentificationTypeDB.active.is_(True))
    return query.order_by(IdentificationTypeDB.name, IdentificationTypeDB.code).all()


def get_identification_type(db: Session, item_id: int) -> IdentificationTypeDB:
    item = db.get(IdentificationTypeDB, item_id)
    if not item:
        _not_found("Tipo de identificación no encontrado.")
    return item


def create_identification_type(
    db: Session,
    data: IdentificationTypeCreate,
) -> IdentificationTypeDB:
    item = IdentificationTypeDB(**data.model_dump())
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


def update_identification_type(
    db: Session,
    item_id: int,
    data: IdentificationTypeUpdate,
) -> IdentificationTypeDB:
    item = get_identification_type(db, item_id)
    values = data.model_dump(exclude_unset=True)

    protected_fields = {
        field
        for field in ("code", "person_type")
        if field in values and values[field] != getattr(item, field)
    }
    if protected_fields:
        referenced = (
            db.query(ClientDB.id)
            .filter(ClientDB.identification_type_id == item.id)
            .first()
        )
        if referenced:
            if "code" in protected_fields:
                _conflict(
                    "No se puede cambiar el código de un tipo de identificación "
                    "que ya está asociado a clientes."
                )
            _conflict(
                "No se puede cambiar el tipo de persona de un tipo de identificación "
                "que ya está asociado a clientes."
            )

    for field, value in values.items():
        setattr(item, field, value)
    _commit(db)
    db.refresh(item)
    return item


def delete_identification_type(db: Session, item_id: int) -> None:
    item = get_identification_type(db, item_id)
    item.active = False
    _commit(db)


def list_countries(
    db: Session,
    include_inactive: bool = False,
) -> list[CountryDB]:
    query = db.query(CountryDB)
    if not include_inactive:
        query = query.filter(CountryDB.active.is_(True))
    return query.order_by(CountryDB.name, CountryDB.code).all()


def get_country(db: Session, item_id: int) -> CountryDB:
    item = db.get(CountryDB, item_id)
    if not item:
        _not_found("País no encontrado.")
    return item


def create_country(db: Session, data: CountryCreate) -> CountryDB:
    item = CountryDB(**data.model_dump())
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


def update_country(
    db: Session,
    item_id: int,
    data: CountryUpdate,
) -> CountryDB:
    item = get_country(db, item_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    _commit(db)
    db.refresh(item)
    return item


def delete_country(db: Session, item_id: int) -> None:
    item = get_country(db, item_id)
    item.active = False
    _commit(db)


def list_departments(
    db: Session,
    country_id: int | None = None,
    include_inactive: bool = False,
) -> list[DepartmentDB]:
    query = db.query(DepartmentDB)
    if not include_inactive:
        query = query.filter(DepartmentDB.active.is_(True))
    if country_id is not None:
        query = query.filter(DepartmentDB.country_id == country_id)
    return query.order_by(DepartmentDB.name, DepartmentDB.code).all()


def get_department(db: Session, item_id: int) -> DepartmentDB:
    item = db.get(DepartmentDB, item_id)
    if not item:
        _not_found("Departamento no encontrado.")
    return item


def _require_active_country(db: Session, country_id: int) -> CountryDB:
    country = get_country(db, country_id)
    if not country.active:
        _conflict("El país seleccionado está inactivo.")
    return country


def create_department(
    db: Session,
    data: DepartmentCreate,
) -> DepartmentDB:
    _require_active_country(db, data.country_id)
    item = DepartmentDB(**data.model_dump())
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


def update_department(
    db: Session,
    item_id: int,
    data: DepartmentUpdate,
) -> DepartmentDB:
    item = get_department(db, item_id)
    values = data.model_dump(exclude_unset=True)
    if "country_id" in values:
        _require_active_country(db, values["country_id"])
    for field, value in values.items():
        setattr(item, field, value)
    _commit(db)
    db.refresh(item)
    return item


def delete_department(db: Session, item_id: int) -> None:
    item = get_department(db, item_id)
    item.active = False
    _commit(db)


def list_cities(
    db: Session,
    department_id: int | None = None,
    include_inactive: bool = False,
) -> list[CityDB]:
    query = db.query(CityDB)
    if not include_inactive:
        query = query.filter(CityDB.active.is_(True))
    if department_id is not None:
        query = query.filter(CityDB.department_id == department_id)
    return query.order_by(CityDB.name, CityDB.code).all()


def get_city(db: Session, item_id: int) -> CityDB:
    item = db.get(CityDB, item_id)
    if not item:
        _not_found("Ciudad o municipio no encontrado.")
    return item


def _require_active_department(db: Session, department_id: int) -> DepartmentDB:
    department = get_department(db, department_id)
    if not department.active:
        _conflict("El departamento seleccionado está inactivo.")
    if not department.country or not department.country.active:
        _conflict("El país asociado al departamento está inactivo.")
    return department


def create_city(db: Session, data: CityCreate) -> CityDB:
    _require_active_department(db, data.department_id)
    item = CityDB(**data.model_dump())
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


def update_city(
    db: Session,
    item_id: int,
    data: CityUpdate,
) -> CityDB:
    item = get_city(db, item_id)
    values = data.model_dump(exclude_unset=True)
    if "department_id" in values:
        _require_active_department(db, values["department_id"])
    for field, value in values.items():
        setattr(item, field, value)
    _commit(db)
    db.refresh(item)
    return item


def delete_city(db: Session, item_id: int) -> None:
    item = get_city(db, item_id)
    item.active = False
    _commit(db)
