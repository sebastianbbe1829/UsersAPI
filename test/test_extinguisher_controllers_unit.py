from unittest.mock import MagicMock

from UsersAPI.controllers import diagnostics_controller
from UsersAPI.controllers import extinguisher_controller as ec
from UsersAPI.controllers import extinguisher_inspection_controller as eic
from UsersAPI.controllers import extinguisher_inspection_item_controller as eiic
from UsersAPI.controllers import extinguisher_type_controller as etc
from UsersAPI.models import GlobalUserDB


def test_diagnostics_controller_authorization_and_delegation(monkeypatch):
    request = object()
    service = MagicMock(return_value={"ip": "1.2.3.4"})
    monkeypatch.setattr(
        diagnostics_controller,
        "get_client_ip_diagnostic_service",
        service,
    )
    current = GlobalUserDB()
    assert diagnostics_controller.get_client_ip_diagnostic(request, current) == {
        "ip": "1.2.3.4"
    }
    service.assert_called_once_with(request)


def test_diagnostics_controller_rejects_non_super():
    from fastapi import HTTPException

    try:
        diagnostics_controller.get_client_ip_diagnostic(object(), object())
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("Expected HTTPException")


def test_extinguisher_controller_delegates(monkeypatch):
    db = MagicMock()
    user = MagicMock()
    data = MagicMock()
    user_tenant = SimpleNamespace(tenant_id=1)
    calls = {
        "create_extinguisher": ((data, db, user), {}),
        "list_extinguishers": ((db, 1, True), {}),
        "search_extinguishers": ((db, 1, "x", 7), {}),
        "get_extinguisher": ((2, db, 1), {}),
        "update_extinguisher": ((2, data, db, user), {}),
        "delete_extinguisher": ((2, db, user), {}),
    }
    functions = {
        "create_extinguisher": ec.crear_extintor,
        "list_extinguishers": ec.listar_extintores,
        "search_extinguishers": ec.buscar_extintores,
        "get_extinguisher": ec.obtener_extintor,
        "update_extinguisher": ec.actualizar_extintor,
        "delete_extinguisher": ec.eliminar_extintor,
    }
    for name, (args, kwargs) in calls.items():
        target = MagicMock(return_value=name)
        monkeypatch.setattr(ec, name, target)
        result = functions[name](*args)
        assert result == name
        target.assert_called_once_with(*args, **kwargs)

    target = MagicMock(return_value="export_extinguishers")
    monkeypatch.setattr(ec, "export_extinguishers", target)
    assert ec.exportar_extintores(db, user, user_tenant) == "export_extinguishers"
    target.assert_called_once_with(db, user, 1)


def test_inspection_controller_delegates(monkeypatch):
    db = MagicMock()
    user = MagicMock()
    data = MagicMock()
    cases = [
        ("list_inspection_items", eic.listar_items_revision, (db,)),
        ("list_inspections", eic.listar_revisiones, (db, 1, 2)),
        ("get_inspection", eic.obtener_revision, (3, db, 1)),
        ("create_inspection", eic.crear_revision, (4, data, db, user)),
    ]
    for name, func, args in cases:
        target = MagicMock(return_value=name)
        monkeypatch.setattr(eic, name, target)
        assert func(*args) == name
        target.assert_called_once_with(*args)


def test_inspection_item_controller_delegates(monkeypatch):
    db = MagicMock()
    data = MagicMock()
    cases = [
        ("list_inspection_items", eiic.listar_items_revision, (db,)),
        ("get_inspection_item", eiic.obtener_item_revision, (3, db)),
        ("create_inspection_item", eiic.crear_item_revision, (data, db)),
        ("update_inspection_item", eiic.actualizar_item_revision, (3, data, db)),
        ("delete_inspection_item", eiic.desactivar_item_revision, (3, db)),
    ]
    for name, func, args in cases:
        target = MagicMock(return_value=name)
        monkeypatch.setattr(eiic, name, target)
        assert func(*args) == name
        target.assert_called_once_with(*args)


def test_type_controller_delegates(monkeypatch):
    db = MagicMock()
    data = MagicMock()
    cases = [
        ("list_extinguisher_types", etc.listar_tipos_extintor, (db,)),
        ("create_extinguisher_type", etc.crear_tipo_extintor, (data, db)),
        ("update_extinguisher_type", etc.actualizar_tipo_extintor, (3, data, db)),
        ("delete_extinguisher_type", etc.eliminar_tipo_extintor, (3, db)),
    ]
    for name, func, args in cases:
        target = MagicMock(return_value=name)
        monkeypatch.setattr(etc, name, target)
        assert func(*args) == name
        target.assert_called_once_with(*args)
