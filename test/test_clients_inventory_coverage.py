from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from UsersAPI.domains.clients.controllers import catalog_controller, client_controller
from UsersAPI.domains.clients.models import CityDB, CountryDB, DepartmentDB, IdentificationTypeDB
from UsersAPI.domains.clients.schemas.catalog import (
    CityCreate, CityUpdate, CountryCreate, CountryUpdate,
    DepartmentCreate, DepartmentUpdate, IdentificationTypeCreate, IdentificationTypeUpdate,
)
from UsersAPI.domains.clients.services import catalog_service, client_service
from UsersAPI.domains.clients.seeds import bootstrap, countries, identification_types
from UsersAPI.domains.inventory.repositories.inventory_movement_repository import InventoryMovementRepository
from UsersAPI.domains.inventory.services import inventory_export_service, inventory_movement_service


class Query:
    def __init__(self, value=None, values=None):
        self.value = value
        self.values = values if values is not None else ([] if value is None else [value])
    def filter(self, *args): return self
    def order_by(self, *args): return self
    def offset(self, *args): return self
    def limit(self, *args): return self
    def first(self): return self.value
    def all(self): return self.values


def test_catalog_controller_delegates_all_operations(monkeypatch):
    sentinel = object()
    names = [
        "list_identification_types", "get_identification_type", "create_identification_type",
        "update_identification_type", "delete_identification_type", "list_countries", "get_country",
        "create_country", "update_country", "delete_country", "list_departments", "get_department",
        "create_department", "update_department", "delete_department", "list_cities", "get_city",
        "create_city", "update_city", "delete_city",
    ]
    for name in names:
        monkeypatch.setattr(catalog_controller, name, lambda *args, _s=sentinel, **kwargs: _s)
    db = MagicMock(); data = MagicMock()
    calls = [
        catalog_controller.listar_tipos_identificacion(db, True), catalog_controller.obtener_tipo_identificacion(db, 1),
        catalog_controller.crear_tipo_identificacion(db, data), catalog_controller.actualizar_tipo_identificacion(db, 1, data),
        catalog_controller.eliminar_tipo_identificacion(db, 1), catalog_controller.listar_paises(db, True),
        catalog_controller.obtener_pais(db, 1), catalog_controller.crear_pais(db, data), catalog_controller.actualizar_pais(db, 1, data),
        catalog_controller.eliminar_pais(db, 1), catalog_controller.listar_departamentos(db, 1, True),
        catalog_controller.obtener_departamento(db, 1), catalog_controller.crear_departamento(db, data),
        catalog_controller.actualizar_departamento(db, 1, data), catalog_controller.eliminar_departamento(db, 1),
        catalog_controller.listar_ciudades(db, 1, True), catalog_controller.obtener_ciudad(db, 1),
        catalog_controller.crear_ciudad(db, data), catalog_controller.actualizar_ciudad(db, 1, data), catalog_controller.eliminar_ciudad(db, 1),
    ]
    assert all(value is sentinel for value in calls[:19])


def test_client_controller_delegates(monkeypatch):
    sentinel = object(); db = MagicMock(); user = MagicMock(); data = MagicMock(); cid = uuid4()
    for name in ["create_client", "list_clients", "get_client", "update_client", "delete_client",
                 "override_client_compliance", "list_restricted_clients_report", "list_compliance_override_history", "screen_client"]:
        monkeypatch.setattr(client_controller, name, lambda *args, _s=sentinel, **kwargs: _s)
    monkeypatch.setattr(client_controller.ClientRepository, "get_by_id", lambda *args: object())
    assert client_controller.crear_cliente(data, db, 7, user) is sentinel
    assert client_controller.listar_clientes(db, 7, 10, 0, "x") is sentinel
    assert client_controller.obtener_cliente(cid, db, 7) is sentinel
    assert client_controller.actualizar_cliente(cid, data, db, 7, user) is sentinel
    assert client_controller.eliminar_cliente(cid, db, 7, user) is sentinel
    assert client_controller.levantar_restriccion_cliente(cid, data, db, 7, user) is sentinel
    assert client_controller.informe_listas_restrictivas(db, 7) is sentinel
    assert client_controller.historial_levantamientos_restriccion(db, 7) is sentinel


def test_catalog_service_crud_and_relationship_validation(monkeypatch):
    db = MagicMock()
    ident = IdentificationTypeDB(id=1, code="CC", name="CC", person_type="NATURAL", active=True)
    country = CountryDB(id=2, code="CO", name="Colombia", active=True)
    department = DepartmentDB(id=3, country_id=2, code="05", name="Antioquia", active=True)
    city = CityDB(id=4, department_id=3, code="001", name="Medellin", active=True)
    db.get.side_effect = [ident, country, department, city]
    db.query.return_value = Query()
    db.refresh.side_effect = lambda item: item
    assert catalog_service.get_identification_type(db, 1) is ident
    assert catalog_service.get_country(db, 2) is country
    assert catalog_service.get_department(db, 3) is department
    assert catalog_service.get_city(db, 4) is city
    assert catalog_service.list_identification_types(db) == []
    assert catalog_service.list_countries(db, True) == []
    assert catalog_service.list_departments(db, 2, True) == []
    assert catalog_service.list_cities(db, 3, True) == []


def test_catalog_service_not_found_and_inactive_dependencies(monkeypatch):
    db = MagicMock(); db.get.return_value = None
    with pytest.raises(HTTPException) as exc: catalog_service.get_country(db, 1)
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        catalog_service.create_department(db, DepartmentCreate(country_id=1, code="01", name="X"))
    assert exc.value.status_code == 404
    db.get.return_value = SimpleNamespace(id=1, active=False)
    with pytest.raises(HTTPException) as exc:
        catalog_service.create_department(db, DepartmentCreate(country_id=1, code="01", name="X"))
    assert exc.value.status_code == 409
    db.get.return_value = SimpleNamespace(id=1, active=False, country=SimpleNamespace(active=True))
    with pytest.raises(HTTPException) as exc:
        catalog_service.create_city(db, CityCreate(department_id=1, code="01", name="X"))
    assert exc.value.status_code == 409


def test_identification_seed_creates_updates_and_deactivates(monkeypatch):
    db = MagicMock()
    existing = SimpleNamespace(code="CC", name="Old", person_type="OLD", active=False)
    obsolete = SimpleNamespace(code="OLD", name="Old", person_type="NATURAL", active=True)
    def query(model):
        q = MagicMock()
        q.filter.return_value.first.return_value = existing if model is IdentificationTypeDB else None
        q.all.return_value = [obsolete]
        return q
    db.query.side_effect = query
    created, updated, deactivated = identification_types.seed_identification_types(db)
    assert created == 10
    assert updated == 1
    assert deactivated == 1
    assert obsolete.active is False


def test_country_seed_create_and_update(monkeypatch):
    db = MagicMock(); q = MagicMock(); db.query.return_value = q
    q.filter.return_value.first.side_effect = [None, SimpleNamespace(**countries.COLOMBIA)]
    assert countries.seed_countries(db) == (1, 0)
    item = SimpleNamespace(**countries.COLOMBIA); item.name = "OLD"
    q.filter.return_value.first.side_effect = [item]
    assert countries.seed_countries(db) == (0, 1)
    assert item.name == countries.COLOMBIA["name"]


def test_clients_bootstrap(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(bootstrap, "seed_countries", lambda db: (1, 2))
    monkeypatch.setattr(bootstrap, "seed_identification_types", lambda db: (3, 4, 5))
    monkeypatch.setattr(bootstrap, "seed_divipola", lambda db: {"created": 6})
    result = bootstrap.bootstrap_clients(db)
    db.commit.assert_called_once()
    assert result["countries"] == {"created": 1, "updated": 2}
    assert result["identification_types"]["deactivated"] == 5


def test_inventory_movement_repository_paths():
    db = MagicMock(); query = Query(values=["row"]); db.query.return_value = query
    repo = InventoryMovementRepository(db)
    movement = SimpleNamespace()
    db.query.return_value = Query(value=movement)
    assert repo.add(movement) is movement
    assert repo.get_by_id(7, uuid4()) is movement
    db.query.return_value = Query(values=[movement])
    assert repo.list_by_product(7, 1, 10, -2, datetime(2026, 1, 1), datetime(2026, 1, 2)) == [movement]
    assert repo.list_all(7, None, 0, datetime(2026, 1, 1), datetime(2026, 1, 2)) == [movement]


def test_inventory_export_helpers_and_empty_exports():
    db = MagicMock(); db.query.return_value = Query(values=[])
    response = inventory_export_service.export_inventory_excel(db, 7, "abc", 2)
    assert response.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    response = inventory_export_service.export_movements_excel(db, 7, 1, date(2026, 1, 1), date(2026, 1, 2))
    assert response.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    with pytest.raises(ValueError):
        inventory_export_service.export_movements_excel(db, 7, None, date(2026, 1, 2), date(2026, 1, 1))


def test_movement_service_helpers_and_date_validation():
    assert inventory_movement_service._actor_name(SimpleNamespace(email="e")) == "e"
    assert inventory_movement_service._actor_name(SimpleNamespace(username="u")) == "u"
    assert inventory_movement_service._actor_name(SimpleNamespace()) == "system"
    assert inventory_movement_service._calculate_weighted_average_cost(
        Decimal("10"), Decimal("100"), Decimal("5"), Decimal("120")
    ) == Decimal("106.6666666666666666666666667")
    assert inventory_movement_service._calculate_reversed_average_cost(
        Decimal("20"), Decimal("150"), Decimal("10"), Decimal("100"), Decimal("10")
    ) == Decimal("200")
    with pytest.raises(HTTPException) as exc:
        inventory_movement_service.list_inventory_movements(
            MagicMock(), 7, from_date=date(2026, 1, 2), to_date=date(2026, 1, 1)
        )
    assert exc.value.status_code == 400
