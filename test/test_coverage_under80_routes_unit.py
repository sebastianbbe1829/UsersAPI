import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4


def test_client_routes_delegate_all_endpoints():
    from UsersAPI.domains.clients.routes.client_routes import client_routes

    db = MagicMock()
    user = SimpleNamespace(tenant_id=9)
    client_id = uuid4()
    data = MagicMock()

    def route(path, method):
        return next(
            r for r in client_routes.routes if r.path == path and method in r.methods
        )

    with patch.multiple(
        "UsersAPI.domains.clients.routes.client_routes",
        crear_cliente=MagicMock(return_value="created"),
        listar_clientes=MagicMock(return_value="listed"),
        informe_listas_restrictivas=MagicMock(return_value="report"),
        historial_levantamientos_restriccion=MagicMock(return_value="history"),
        obtener_cliente=MagicMock(return_value="got"),
        actualizar_cliente=MagicMock(return_value="updated"),
        revisar_cliente_listas=MagicMock(return_value="screened"),
        levantar_restriccion_cliente=MagicMock(return_value="override"),
        eliminar_cliente=MagicMock(),
    ) as mocks:
        assert asyncio.run(
            route("/clients", "POST").endpoint(data, db, user, user)
        ) == "created"
        assert asyncio.run(
            route("/clients", "GET").endpoint(2, 5, "abc", db, user)
        ) == "listed"
        assert asyncio.run(
            route("/clients/restricted-report", "GET").endpoint(db, user)
        ) == "report"
        assert asyncio.run(
            route("/clients/compliance/override-history", "GET").endpoint(db, user)
        ) == "history"
        assert asyncio.run(
            route("/clients/{client_id}", "GET").endpoint(client_id, db, user)
        ) == "got"
        assert asyncio.run(
            route("/clients/{client_id}", "PATCH").endpoint(
                client_id, data, db, user, user
            )
        ) == "updated"
        assert asyncio.run(
            route("/clients/{client_id}/compliance/screen", "POST").endpoint(
                client_id, db, user
            )
        ) == "screened"
        assert asyncio.run(
            route("/clients/{client_id}/compliance/override", "POST").endpoint(
                client_id, data, db, user, user
            )
        ) == "override"
        assert asyncio.run(
            route("/clients/{client_id}", "DELETE").endpoint(
                client_id, db, user, user
            )
        ) is None

        assert mocks["listar_clientes"].call_args.kwargs == {
            "limit": 5,
            "offset": 5,
            "search": "abc",
        }


def test_sales_permissions_module_is_importable():
    import UsersAPI.security.sales_permissions as sales_permissions

    assert sales_permissions is not None
