import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from UsersAPI.domains.portfolio.routes.portfolio_routes import portfolio_routes
from UsersAPI.domains.sales.routes.sale_routes import sales_routes


def _route(router, path: str, method: str = "GET"):
    return next(
        route for route in router.routes if route.path == path and method in route.methods
    )


def _permission_code(route) -> str:
    dependency = route.dependencies[0]
    checker = dependency.dependency
    closure = checker.__closure__ or ()
    return next(cell.cell_contents for cell in closure if isinstance(cell.cell_contents, str))


def test_sales_operational_routes_use_sales_create_permission():
    assert _permission_code(_route(sales_routes, "/sales/pos/catalog")) == "SALES_CREATE"
    assert _permission_code(_route(sales_routes, "/sales/pos/clients")) == "SALES_CREATE"
    assert (
        _permission_code(
            _route(sales_routes, "/sales/pos/clients/{client_id}/credit")
        )
        == "SALES_CREATE"
    )


def test_portfolio_payment_operational_routes_use_payment_create_permission():
    assert (
        _permission_code(_route(portfolio_routes, "/portfolio/payments/clients"))
        == "PORTFOLIO_PAYMENT_CREATE"
    )
    assert (
        _permission_code(
            _route(portfolio_routes, "/portfolio/payments/clients/{client_id}/obligations")
        )
        == "PORTFOLIO_PAYMENT_CREATE"
    )


def test_sales_pos_catalog_route_delegates_to_operational_service():
    route = _route(sales_routes, "/sales/pos/catalog")
    db = MagicMock()
    tenant = SimpleNamespace(tenant_id=17)
    expected = MagicMock()

    with patch(
        "UsersAPI.domains.sales.routes.sale_routes.get_pos_catalog",
        return_value=expected,
    ) as service:
        result = asyncio.run(route.endpoint(db=db, user_tenant=tenant))

    assert result is expected
    service.assert_called_once_with(db, 17)


def test_sales_pos_clients_route_delegates_to_operational_service():
    route = _route(sales_routes, "/sales/pos/clients")
    db = MagicMock()
    tenant = SimpleNamespace(tenant_id=17)
    client_id = uuid4()
    client = SimpleNamespace(
        id=client_id,
        full_name="Cliente de prueba",
        identification_number="123",
        status="ACTIVE",
        email="cliente@example.com",
    )

    with patch(
        "UsersAPI.domains.sales.routes.sale_routes.search_pos_clients",
        return_value=[client],
    ) as service:
        result = asyncio.run(
            route.endpoint(
                search="cliente",
                limit=20,
                offset=0,
                db=db,
                user_tenant=tenant,
            )
        )

    assert len(result) == 1
    assert result[0].id == str(client_id)
    assert result[0].full_name == "Cliente de prueba"
    service.assert_called_once_with(
        db,
        17,
        search="cliente",
        limit=20,
        offset=0,
    )


def test_sales_pos_credit_route_delegates_to_operational_service():
    route = _route(sales_routes, "/sales/pos/clients/{client_id}/credit")
    db = MagicMock()
    tenant = SimpleNamespace(tenant_id=17)
    client_id = UUID("11111111-1111-1111-1111-111111111111")
    credit = SimpleNamespace(
        approved_limit=100000,
        credit_used=25000,
        credit_available=75000,
    )

    with patch(
        "UsersAPI.domains.sales.routes.sale_routes.get_pos_client_credit",
        return_value=credit,
    ) as service:
        result = asyncio.run(
            route.endpoint(
                client_id=client_id,
                db=db,
                user_tenant=tenant,
            )
        )

    assert result.client_id == str(client_id)
    assert result.approved_limit == 100000
    assert result.credit_used == 25000
    assert result.credit_available == 75000
    service.assert_called_once_with(client_id, db, 17)


def test_portfolio_payment_clients_route_delegates_to_operational_service():
    route = _route(portfolio_routes, "/portfolio/payments/clients")
    db = MagicMock()
    tenant = SimpleNamespace(tenant_id=17)
    client_id = uuid4()
    client = SimpleNamespace(
        id=client_id,
        full_name="Cliente cartera",
        identification_number="456",
        status="ACTIVE",
        email=None,
    )

    with patch(
        "UsersAPI.domains.portfolio.routes.portfolio_routes.search_payment_clients",
        return_value=[client],
    ) as service:
        result = asyncio.run(
            route.endpoint(
                search="cartera",
                limit=20,
                offset=0,
                db=db,
                user_tenant=tenant,
            )
        )

    assert len(result) == 1
    assert result[0].id == str(client_id)
    assert result[0].full_name == "Cliente cartera"
    assert result[0].email is None
    service.assert_called_once_with(
        db,
        17,
        search="cartera",
        limit=20,
        offset=0,
    )


def test_portfolio_payment_obligations_route_delegates_to_operational_service():
    route = _route(
        portfolio_routes,
        "/portfolio/payments/clients/{client_id}/obligations",
    )
    db = MagicMock()
    tenant = SimpleNamespace(tenant_id=17)
    client_id = UUID("22222222-2222-2222-2222-222222222222")
    expected = [MagicMock()]

    with patch(
        "UsersAPI.domains.portfolio.routes.portfolio_routes.get_payment_client_obligations",
        return_value=expected,
    ) as service:
        result = asyncio.run(
            route.endpoint(
                client_id=client_id,
                db=db,
                user_tenant=tenant,
            )
        )

    assert result is expected
    service.assert_called_once_with(client_id, db, 17)
