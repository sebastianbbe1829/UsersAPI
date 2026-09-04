from unittest.mock import MagicMock

from UsersAPI.domains.clients.models import (
    CityDB,
    CountryDB,
    DepartmentDB,
    IdentificationTypeDB,
)
from UsersAPI.domains.clients.services.catalog_service import (
    list_cities,
    list_countries,
    list_departments,
    list_identification_types,
)


def _query_mock(result):
    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.all.return_value = result
    return query


def test_list_identification_types_returns_only_active_catalog_rows():
    db = MagicMock()
    rows = [IdentificationTypeDB(id=1, code="CC", name="Cédula de ciudadanía", person_type="NATURAL")]
    db.query.return_value = _query_mock(rows)

    result = list_identification_types(db)

    assert result == rows
    db.query.assert_called_once_with(IdentificationTypeDB)


def test_list_countries_returns_only_active_catalog_rows():
    db = MagicMock()
    rows = [CountryDB(id=1, code="CO", name="Colombia")]
    db.query.return_value = _query_mock(rows)

    result = list_countries(db)

    assert result == rows
    db.query.assert_called_once_with(CountryDB)


def test_list_departments_without_country_filter():
    db = MagicMock()
    rows = [DepartmentDB(id=1, country_id=1, code="05", name="Antioquia")]
    query = _query_mock(rows)
    db.query.return_value = query

    result = list_departments(db)

    assert result == rows
    query.filter.assert_called_once()
    query.order_by.assert_called_once()


def test_list_departments_filters_by_country():
    db = MagicMock()
    rows = [DepartmentDB(id=1, country_id=1, code="05", name="Antioquia")]
    query = _query_mock(rows)
    db.query.return_value = query

    result = list_departments(db, country_id=1)

    assert result == rows
    assert query.filter.call_count == 2


def test_list_cities_without_department_filter():
    db = MagicMock()
    rows = [CityDB(id=1, department_id=1, code="001", name="Medellín")]
    query = _query_mock(rows)
    db.query.return_value = query

    result = list_cities(db)

    assert result == rows
    query.filter.assert_called_once()
    query.order_by.assert_called_once()


def test_list_cities_filters_by_department():
    db = MagicMock()
    rows = [CityDB(id=1, department_id=1, code="001", name="Medellín")]
    query = _query_mock(rows)
    db.query.return_value = query

    result = list_cities(db, department_id=1)

    assert result == rows
    assert query.filter.call_count == 2
