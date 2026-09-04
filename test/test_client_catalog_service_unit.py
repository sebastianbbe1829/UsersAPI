from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from UsersAPI.domains.clients.models import (
    CityDB,
    ClientDB,
    CountryDB,
    DepartmentDB,
    IdentificationTypeDB,
)
from UsersAPI.domains.clients.schemas.catalog import IdentificationTypeUpdate
from UsersAPI.domains.clients.services.catalog_service import (
    delete_identification_type,
    list_cities,
    list_countries,
    list_departments,
    list_identification_types,
    update_identification_type,
)


def _query_mock(result):
    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.all.return_value = result
    query.first.return_value = result
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


def test_update_identification_type_allows_code_change_when_not_referenced():
    db = MagicMock()
    item = IdentificationTypeDB(id=1, code="OLD", name="Antiguo", person_type="NATURAL")
    db.get.return_value = item
    query = _query_mock(None)
    db.query.return_value = query

    result = update_identification_type(
        db,
        1,
        IdentificationTypeUpdate(code="NEW"),
    )

    assert result.code == "NEW"
    db.commit.assert_called_once()


def test_update_identification_type_rejects_code_change_when_referenced_by_client():
    db = MagicMock()
    item = IdentificationTypeDB(id=1, code="CC", name="Cédula", person_type="NATURAL")
    db.get.return_value = item
    db.query.return_value = _query_mock((1,))

    with pytest.raises(HTTPException) as exc:
        update_identification_type(
            db,
            1,
            IdentificationTypeUpdate(code="CC_NEW"),
        )

    assert exc.value.status_code == 409
    assert "código" in exc.value.detail
    db.commit.assert_not_called()


def test_update_identification_type_does_not_query_clients_when_code_is_unchanged():
    db = MagicMock()
    item = IdentificationTypeDB(id=1, code="CC", name="Cédula", person_type="NATURAL")
    db.get.return_value = item

    result = update_identification_type(
        db,
        1,
        IdentificationTypeUpdate(code="CC", name="Cédula de ciudadanía"),
    )

    assert result.name == "Cédula de ciudadanía"
    db.query.assert_not_called()
    db.commit.assert_called_once()


def test_delete_identification_type_soft_deletes_catalog_row():
    db = MagicMock()
    item = IdentificationTypeDB(id=1, code="CC", name="Cédula", person_type="NATURAL", active=True)
    db.get.return_value = item

    delete_identification_type(db, 1)

    assert item.active is False
    db.commit.assert_called_once()


def test_update_identification_type_uses_client_fk_reference_check():
    db = MagicMock()
    item = IdentificationTypeDB(id=1, code="CC", name="Cédula", person_type="NATURAL")
    db.get.return_value = item
    query = _query_mock(None)
    db.query.return_value = query

    update_identification_type(db, 1, IdentificationTypeUpdate(name="Cédula de ciudadanía"))

    db.query.assert_not_called()
    assert ClientDB.identification_type_id is not None
