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
    checker = dependency.call
    closure = checker.__closure__ or ()
    return next(
        cell.cell_contents
        for cell in closure
        if isinstance(cell.cell_contents, str)
    )


def test_catalog_routes_are_registered_as_read_only_get_endpoints():
    paths = {route.path for route in catalog_routes.routes}

    assert paths == {
        "/clients/catalogs/identification-types",
        "/clients/catalogs/countries",
        "/clients/catalogs/departments",
        "/clients/catalogs/cities",
    }
    assert all(route.methods == {"GET"} for route in catalog_routes.routes)


def test_all_catalog_routes_require_client_read_permission():
    assert all(_permission_code(route) == "CLIENT_READ" for route in catalog_routes.routes)


def test_identification_types_route_delegates_to_controller():
    route = _route("/clients/catalogs/identification-types")
    db = MagicMock()
    expected = [MagicMock()]

    with patch(
        "UsersAPI.domains.clients.routes.catalog_routes.listar_tipos_identificacion",
        return_value=expected,
    ) as controller:
        result = route.endpoint(db)

    assert result == expected
    controller.assert_called_once_with(db)


def test_countries_route_delegates_to_controller():
    route = _route("/clients/catalogs/countries")
    db = MagicMock()
    expected = [MagicMock()]

    with patch(
        "UsersAPI.domains.clients.routes.catalog_routes.listar_paises",
        return_value=expected,
    ) as controller:
        result = route.endpoint(db)

    assert result == expected
    controller.assert_called_once_with(db)


def test_departments_route_passes_country_filter():
    route = _route("/clients/catalogs/departments")
    db = MagicMock()
    expected = [MagicMock()]

    with patch(
        "UsersAPI.domains.clients.routes.catalog_routes.listar_departamentos",
        return_value=expected,
    ) as controller:
        result = route.endpoint(5, db)

    assert result == expected
    controller.assert_called_once_with(db, 5)


def test_cities_route_passes_department_filter():
    route = _route("/clients/catalogs/cities")
    db = MagicMock()
    expected = [MagicMock()]

    with patch(
        "UsersAPI.domains.clients.routes.catalog_routes.listar_ciudades",
        return_value=expected,
    ) as controller:
        result = route.endpoint(7, db)

    assert result == expected
    controller.assert_called_once_with(db, 7)
