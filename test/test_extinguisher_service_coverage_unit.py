from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from UsersAPI.services import extinguisher_service


def _datos(**overrides):
    values = {
        "code": " e-01 ",
        "extinguisher_type_id": 2,
        "capacity": "10 lb",
        "location": "P1",
        "last_recharge_date": None,
        "next_recharge_date": None,
        "last_hydrostatic_test_date": None,
        "next_hydrostatic_test_date": None,
        "status": " activo ",
        "is_stock": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_extinguisher_service_validation_and_create(monkeypatch):
    db = MagicMock()
    type_query = MagicMock()
    type_query.filter.return_value = type_query
    type_query.first.return_value = SimpleNamespace(id=2, active=True)
    db.query.return_value = type_query
    repo = MagicMock()
    repo.get_by_code_and_tenant.return_value = None
    repo.add.side_effect = lambda item: item
    monkeypatch.setattr(
        extinguisher_service,
        "ExtinguisherRepository",
        MagicMock(return_value=repo),
    )
    user_tenant = SimpleNamespace(tenant_id=7)

    result = extinguisher_service.create_extinguisher(_datos(), db, user_tenant)
    assert result.code == "E-01"
    assert result.status == "ACTIVO"
    assert result.tenant_id == 7
    repo.add.assert_called_once()
    db.refresh.assert_called_once_with(result)

    type_query.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        extinguisher_service.create_extinguisher(
            _datos(code="E-02"), db, user_tenant
        )
    assert exc.value.status_code == 400

    repo.get_by_code_and_tenant.return_value = SimpleNamespace(id=99)
    with pytest.raises(HTTPException) as exc:
        extinguisher_service.create_extinguisher(
            _datos(code="E-03"), db, user_tenant
        )
    assert exc.value.status_code == 409

    repo.get_by_code_and_tenant.return_value = None
    with pytest.raises(HTTPException) as exc:
        extinguisher_service.create_extinguisher(
            _datos(code="   "), db, user_tenant
        )
    assert exc.value.status_code == 400


def test_extinguisher_service_integrity_error_and_simple_queries(monkeypatch):
    db = MagicMock()
    type_query = MagicMock()
    type_query.filter.return_value = type_query
    type_query.first.return_value = SimpleNamespace(id=2, active=True)
    db.query.return_value = type_query
    repo = MagicMock()
    repo.get_by_code_and_tenant.return_value = None
    repo.add.side_effect = IntegrityError("stmt", {}, Exception("duplicate"))
    monkeypatch.setattr(
        extinguisher_service,
        "ExtinguisherRepository",
        MagicMock(return_value=repo),
    )
    with pytest.raises(HTTPException) as exc:
        extinguisher_service.create_extinguisher(
            _datos(), db, SimpleNamespace(tenant_id=7)
        )
    assert exc.value.status_code == 409
    db.rollback.assert_called_once()

    repo.get_all_by_tenant.return_value = [1]
    assert extinguisher_service.list_extinguishers(db, 7, True) == [1]
    repo.search_by_tenant.return_value = [2]
    assert extinguisher_service.search_extinguishers(db, 7, "abc", 5) == [2]


def test_extinguisher_service_get_update_and_delete(monkeypatch):
    db = MagicMock()
    repo = MagicMock()
    extinguisher = SimpleNamespace(
        id=4,
        code="OLD",
        extinguisher_type_id=2,
        status="ACTIVO",
        active=True,
    )
    repo.get_by_id_and_tenant.return_value = extinguisher
    repo.get_by_code_and_tenant.return_value = None
    monkeypatch.setattr(
        extinguisher_service,
        "ExtinguisherRepository",
        MagicMock(return_value=repo),
    )
    type_query = MagicMock()
    type_query.filter.return_value = type_query
    type_query.first.return_value = SimpleNamespace(id=3, active=True)
    db.query.return_value = type_query

    assert extinguisher_service.get_extinguisher(4, db, 7) is extinguisher
    datos = SimpleNamespace(
        model_dump=lambda exclude_unset: {
            "code": " new ",
            "extinguisher_type_id": 3,
            "status": "inactivo",
        }
    )
    assert (
        extinguisher_service.update_extinguisher(
            4, datos, db, SimpleNamespace(tenant_id=7)
        )
        is extinguisher
    )
    assert extinguisher.code == "NEW"
    assert extinguisher.status == "INACTIVO"
    repo.update.assert_called_once_with(extinguisher)
    db.refresh.assert_called_once_with(extinguisher)

    repo.get_by_id_and_tenant.return_value = None
    with pytest.raises(HTTPException) as exc:
        extinguisher_service.get_extinguisher(4, db, 7)
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        extinguisher_service.update_extinguisher(
            4, datos, db, SimpleNamespace(tenant_id=7)
        )
    assert exc.value.status_code == 404

    repo.get_by_id_and_tenant.return_value = extinguisher
    repo.get_by_code_and_tenant.return_value = SimpleNamespace(id=99)
    duplicate_data = SimpleNamespace(
        model_dump=lambda exclude_unset: {"code": "DUP"}
    )
    with pytest.raises(HTTPException) as exc:
        extinguisher_service.update_extinguisher(
            4,
            duplicate_data,
            db,
            SimpleNamespace(tenant_id=7),
        )
    assert exc.value.status_code == 409

    repo.get_by_code_and_tenant.return_value = None
    assert (
        extinguisher_service.delete_extinguisher(
            4, db, SimpleNamespace(tenant_id=7)
        )["id"]
        == 4
    )
    assert extinguisher.active is False

    repo.get_by_id_and_tenant.return_value = None
    with pytest.raises(HTTPException) as exc:
        extinguisher_service.delete_extinguisher(
            4, db, SimpleNamespace(tenant_id=7)
        )
    assert exc.value.status_code == 404
