from types import SimpleNamespace
from unittest.mock import MagicMock

import asyncio


def test_extinguisher_routes_delegate(monkeypatch):
    routes = __import__(
        "UsersAPI.routes.extinguisher_routes",
        fromlist=["extinguisher_routes"],
    )
    controller = MagicMock()
    monkeypatch.setattr(routes, "extinguisher_controller", controller)
    db = MagicMock()
    tenant = SimpleNamespace(tenant_id=7)
    user = SimpleNamespace(id=9)
    datos = SimpleNamespace()
    controller.crear_extintor.return_value = "create"
    controller.exportar_extintores.return_value = "export"
    controller.buscar_extintores.return_value = "search"
    controller.listar_extintores.return_value = "list"
    controller.obtener_extintor.return_value = "get"
    controller.actualizar_extintor.return_value = "update"
    controller.eliminar_extintor.return_value = "delete"

    assert asyncio.run(routes.crear_extintor(datos, db, tenant)) == "create"
    assert asyncio.run(routes.exportar_extintores(db, user, tenant)) == "export"
    assert asyncio.run(routes.buscar_extintores("abc", 10, db, tenant)) == "search"
    assert asyncio.run(routes.listar_extintores(True, db, tenant)) == "list"
    assert asyncio.run(routes.obtener_extintor(4, db, tenant)) == "get"
    assert asyncio.run(routes.actualizar_extintor(datos, 4, db, tenant)) == "update"
    assert asyncio.run(routes.eliminar_extintor(4, db, tenant)) == "delete"
    controller.crear_extintor.assert_called_once_with(datos, db, tenant)
    controller.exportar_extintores.assert_called_once_with(db, user, tenant)
    controller.buscar_extintores.assert_called_once_with(db, 7, "abc", 10)
    controller.listar_extintores.assert_called_once_with(db, 7, True)
    controller.obtener_extintor.assert_called_once_with(4, db, 7)
    controller.actualizar_extintor.assert_called_once_with(4, datos, db, tenant)
    controller.eliminar_extintor.assert_called_once_with(4, db, tenant)


def test_inspection_item_routes_delegate(monkeypatch):
    routes = __import__(
        "UsersAPI.routes.extinguisher_inspection_item_routes",
        fromlist=["extinguisher_inspection_item_routes"],
    )
    controller = MagicMock()
    monkeypatch.setattr(routes, "extinguisher_inspection_item_controller", controller)
    db = MagicMock()
    datos = SimpleNamespace()
    controller.listar_items_revision.return_value = "list"
    controller.obtener_item_revision.return_value = "get"
    controller.crear_item_revision.return_value = "create"
    controller.actualizar_item_revision.return_value = "update"
    controller.desactivar_item_revision.return_value = "delete"

    assert asyncio.run(routes.listar_items_revision(db)) == "list"
    assert asyncio.run(routes.obtener_item_revision(2, db)) == "get"
    assert asyncio.run(routes.crear_item_revision(datos, db)) == "create"
    assert asyncio.run(routes.actualizar_item_revision(datos, 2, db)) == "update"
    assert asyncio.run(routes.desactivar_item_revision(2, db)) == "delete"
    controller.listar_items_revision.assert_called_once_with(db)
    controller.obtener_item_revision.assert_called_once_with(2, db)
    controller.crear_item_revision.assert_called_once_with(datos, db)
    controller.actualizar_item_revision.assert_called_once_with(2, datos, db)
    controller.desactivar_item_revision.assert_called_once_with(2, db)


def test_inspection_routes_delegate(monkeypatch):
    routes = __import__(
        "UsersAPI.routes.extinguisher_inspection_routes",
        fromlist=["extinguisher_inspection_routes"],
    )
    controller = MagicMock()
    monkeypatch.setattr(routes, "extinguisher_inspection_controller", controller)
    db = MagicMock()
    tenant = SimpleNamespace(tenant_id=7)
    user = SimpleNamespace()
    datos = SimpleNamespace()
    controller.listar_items_revision.return_value = "items"
    controller.listar_revisiones.return_value = "list"
    controller.obtener_revision.return_value = "get"
    controller.crear_revision.return_value = "create"

    assert asyncio.run(routes.listar_items_revision(db)) == "items"
    assert asyncio.run(routes.listar_revisiones(None, db, tenant)) == "list"
    assert asyncio.run(routes.obtener_revision(3, db, tenant)) == "get"
    assert asyncio.run(routes.crear_revision(datos, 4, db, user)) == "create"
    assert asyncio.run(routes.listar_revisiones_extintor(4, db, tenant)) == "list"
    assert asyncio.run(routes.crear_revision_extintor(datos, 4, db, user)) == "create"
    assert controller.listar_items_revision.call_count == 1
    assert controller.listar_revisiones.call_count == 2
    assert controller.obtener_revision.assert_called_once_with(3, db, 7) is None
    assert controller.crear_revision.call_count == 2


def test_extinguisher_type_routes_delegate(monkeypatch):
    routes = __import__(
        "UsersAPI.routes.extinguisher_type_routes",
        fromlist=["extinguisher_type_routes"],
    )
    controller = MagicMock()
    monkeypatch.setattr(routes, "extinguisher_type_controller", controller)
    db = MagicMock()
    datos = SimpleNamespace()
    controller.listar_tipos_extintor.return_value = "list"
    controller.crear_tipo_extintor.return_value = "create"
    controller.actualizar_tipo_extintor.return_value = "update"
    controller.eliminar_tipo_extintor.return_value = "delete"

    assert asyncio.run(routes.listar_tipos_extintor(db)) == "list"
    assert asyncio.run(routes.crear_tipo_extintor(datos, db)) == "create"
    assert asyncio.run(routes.actualizar_tipo_extintor(2, datos, db)) == "update"
    assert asyncio.run(routes.eliminar_tipo_extintor(2, db)) == "delete"
    controller.listar_tipos_extintor.assert_called_once_with(db)
    controller.crear_tipo_extintor.assert_called_once_with(datos, db)
    controller.actualizar_tipo_extintor.assert_called_once_with(2, datos, db)
    controller.eliminar_tipo_extintor.assert_called_once_with(2, db)
