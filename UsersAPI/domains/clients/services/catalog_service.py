from sqlalchemy.orm import Session

from ..models import CityDB, CountryDB, DepartmentDB, IdentificationTypeDB


def list_identification_types(db: Session) -> list[IdentificationTypeDB]:
    return (
        db.query(IdentificationTypeDB)
        .filter(IdentificationTypeDB.active.is_(True))
        .order_by(IdentificationTypeDB.name, IdentificationTypeDB.code)
        .all()
    )


def list_countries(db: Session) -> list[CountryDB]:
    return (
        db.query(CountryDB)
        .filter(CountryDB.active.is_(True))
        .order_by(CountryDB.name, CountryDB.code)
        .all()
    )


def list_departments(
    db: Session,
    country_id: int | None = None,
) -> list[DepartmentDB]:
    query = db.query(DepartmentDB).filter(DepartmentDB.active.is_(True))
    if country_id is not None:
        query = query.filter(DepartmentDB.country_id == country_id)
    return query.order_by(DepartmentDB.name, DepartmentDB.code).all()


def list_cities(
    db: Session,
    department_id: int | None = None,
) -> list[CityDB]:
    query = db.query(CityDB).filter(CityDB.active.is_(True))
    if department_id is not None:
        query = query.filter(CityDB.department_id == department_id)
    return query.order_by(CityDB.name, CityDB.code).all()
