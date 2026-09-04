import asyncio
from unittest.mock import MagicMock, patch

from UsersAPI.domains.clients.routes.catalog_routes import catalog_routes


def _route(path: str, method: str = "GET"):
    return next(
        route
        for route in catalog_routes.routes
        if route.path == path and method in route.methods
    )


def _permission_code(route) -> str:
    dependency = route.dependencies[0]
    checker = dependency.dependency
    closure = checker.__closure__ or ()
    return next(
        cell.cell_contents
        for cell in closure
        if isinstance(cell.cell_contents, str)
    )


def test_catalog_routes_are_registered_with_expected_crud_endpoints():
    paths = {(route.path, next(iter(route.methods))) for route in catalog_routes.routes}

    assert paths == {
        ("/clients/catalogs/identification-types", "GET"),
        ("/clients/catalogs/identification-types", "POST"),
        ("/clients/catalogs/identification-types/{item_id}", "GET"),
        ("/clients/catalogs/identification-types/{item_id}", "PATCH"),
        ("/clients/catalogs/identification-types/{item_id}", "DELETE"),
        ("/clients/catalogs/countries", "GET"),
        ("/clients/catalogs/countries", "POST"),
        ("/clients/catalogs/countries/{item_id}", "GET"),
        ("/clients/catalogs/countries/{item_id}", "PATCH"),
        ("/clients/catalogs/countries/{item_id}", "DELETE"),
        ("/clients/catalogs/departments", "GET"),
        ("/clients/catalogs/departments", "POST"),
        ("/clients/catalogs/departments/{item_id}", "GET"),
        ("/clients/catalogs/departments/{item_id}", "PATCH"),
        ("/clients/catalogs/departments/{item_id}", "DELETE"),
        ("/clients/catalogs/cities", "GET"),
        ("/clients/catalogs/cities", "POST"),
        ("/clients/catalogs/cities/{item_id}", "GET"),
        ("/clients/catalogs/cities/{item_id}", "PATCH"),
        ("/clients/catalogs/cities/{item_id}", "DELETE"),
    }


def test_catalog_routes_require_expected_client_permissions():
    expected_permissions = {
        "GET": "CLIENT_READ",
        "POST": "CLIENT_CREATE",
        "PATCH": "CLIENT_UPDATE",
        "DELETE": "CLIENT_DELETE",
    }

    assert all(
        _permission_code(route) == expected_permissions[next(iter(route.methods))]
        for route in catalog_routes.routes
    )


def test_identification_types_route_delegates_to_controller():
    route = _route("/clients/catalogs/identification-types")
    db = MagicMock()
    expected = [MagicMock()]

    with patch(
        "UsersAPI.domains.clients.routes.catalog_routes.listar_tipos_identificacion",
        return_value=expected,
    ) as controller:
        result = asyncio.run(route.endpoint(db=db, include_inactive=True))

    assert result == expected
    controller.assert_called_once_with(db, True)


def test_countries_route_delegates_to_controller():
    route = _route("/clients/catalogs/countries")
    db = MagicMock()
    expected = [MagicMock()]

    with patch(
        "UsersAPI.domains.clients.routes.catalog_routes.listar_paises",
        return_value=expected,
    ) as controller:
        result = asyncio.run(route.endpoint(db=db, include_inactive=True))

    assert result == expected
    controller.assert_called_once_with(db, True)


def test_departments_route_passes_country_filter():
    route = _route("/clients/catalogs/departments")
    db = MagicMock()
    expected = [MagicMock()]

    with patch(
        "UsersAPI.domains.clients.routes.catalog_routes.listar_departamentos",
        return_value=expected,
    ) as controller:
        result = asyncio.run(
            route.endpoint(country_id=5, db=db, include_inactive=True)
        )

    assert result == expected
    controller.assert_called_once_with(db, 5, True)


def test_cities_route_passes_department_filter():
    route = _route("/clients/catalogs/cities")
    db = MagicMock()
    expected = [MagicMock()]

    with patch(
        "UsersAPI.domains.clients.routes.catalog_routes.listar_ciudades",
        return_value=expected,
    ) as controller:
        result = asyncio.run(
            route.endpoint(department_id=7, db=db, include_inactive=True)
        )

    assert result == expected
    controller.assert_called_once_with(db, 7, True)
