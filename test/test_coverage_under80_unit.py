import asyncio
import csv
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException


def test_catalog_service_crud_and_validation_branches():
    from UsersAPI.domains.clients.models import CityDB, CountryDB, DepartmentDB, IdentificationTypeDB
    from UsersAPI.domains.clients.schemas.catalog import (
        CityCreate,
        CityUpdate,
        CountryCreate,
        CountryUpdate,
        DepartmentCreate,
        DepartmentUpdate,
        IdentificationTypeCreate,
        IdentificationTypeUpdate,
    )
    from UsersAPI.domains.clients.services.catalog_service import (
        create_city,
        create_country,
        create_department,
        create_identification_type,
        delete_city,
        delete_country,
        get_city,
        get_country,
        get_department,
        get_identification_type,
        update_city,
        update_country,
        update_department,
    )

    db = MagicMock()
    db.get.side_effect = [
        IdentificationTypeDB(id=1, code="CC", name="CC", person_type="NATURAL"),
        CountryDB(id=2, code="CO", name="Colombia", active=True),
        DepartmentDB(id=3, country_id=2, code="05", name="Antioquia", active=True),
        CityDB(id=4, department_id=3, code="05001", name="Medellin", active=True),
    ]

    created = create_identification_type(
        db, IdentificationTypeCreate(code="CE", name="Cedula extranjera", person_type="NATURAL")
    )
    assert created.code == "CE"
    created_country = create_country(db, CountryCreate(code="CO", name="Colombia"))
    assert created_country.name == "Colombia"

    db.get.side_effect = [CountryDB(id=2, code="CO", name="Colombia", active=True)]
    created_department = create_department(
        db, DepartmentCreate(country_id=2, code="05", name="Antioquia")
    )
    assert created_department.country_id == 2

    department = DepartmentDB(id=3, country_id=2, code="05", name="Antioquia", active=True)
    department.country = CountryDB(id=2, code="CO", name="Colombia", active=True)
    db.get.side_effect = [department]
    created_city = create_city(
        db, CityCreate(department_id=3, code="05001", name="Medellin", type="Municipio")
    )
    assert created_city.department_id == 3

    db.get.side_effect = [CountryDB(id=2, code="CO", name="Colombia", active=True)]
    assert get_country(db, 2).code == "CO"
    db.get.side_effect = [DepartmentDB(id=3, country_id=2, code="05", name="Antioquia")]
    assert get_department(db, 3).code == "05"
    db.get.side_effect = [CityDB(id=4, department_id=3, code="05001", name="Medellin")]
    assert get_city(db, 4).code == "05001"
    db.get.side_effect = [IdentificationTypeDB(id=1, code="CC", name="CC", person_type="NATURAL")]
    assert get_identification_type(db, 1).code == "CC"

    db.get.side_effect = [CountryDB(id=2, code="CO", name="Colombia", active=True)]
    assert update_country(db, 2, CountryUpdate(name="Colombia nueva")).name == "Colombia nueva"
    db.get.side_effect = [DepartmentDB(id=3, country_id=2, code="05", name="Antioquia", active=True)]
    assert update_department(db, 3, DepartmentUpdate(name="Antioquia nueva")).name == "Antioquia nueva"
    city = CityDB(id=4, department_id=3, code="05001", name="Medellin", active=True)
    db.get.side_effect = [city]
    assert update_city(db, 4, CityUpdate(name="Medellín")).name == "Medellín"

    db.get.side_effect = [CountryDB(id=2, code="CO", name="Colombia", active=True)]
    delete_country(db, 2)
    assert db.get.call_count >= 1
    db.get.side_effect = [DepartmentDB(id=3, country_id=2, code="05", name="Antioquia", active=True)]
    delete_department = __import__(
        "UsersAPI.domains.clients.services.catalog_service", fromlist=["delete_department"]
    ).delete_department
    delete_department(db, 3)
    db.get.side_effect = [CityDB(id=4, department_id=3, code="05001", name="Medellin", active=True)]
    delete_city(db, 4)
    assert db.commit.call_count >= 3

    db.get.side_effect = [CountryDB(id=2, code="CO", name="Colombia", active=False)]
    with pytest.raises(HTTPException):
        create_department(db, DepartmentCreate(country_id=2, code="05", name="Antioquia"))

    inactive_department = DepartmentDB(id=3, country_id=2, code="05", name="Antioquia", active=False)
    inactive_department.country = CountryDB(id=2, code="CO", name="Colombia", active=True)
    db.get.side_effect = [inactive_department]
    with pytest.raises(HTTPException):
        create_city(db, CityCreate(department_id=3, code="05001", name="Medellin", type="Municipio"))

    db.get.side_effect = [IdentificationTypeDB(id=1, code="CC", name="CC", person_type="NATURAL")]
    db.query.return_value.filter.return_value.first.return_value = (1,)
    with pytest.raises(HTTPException):
        from UsersAPI.domains.clients.services.catalog_service import update_identification_type
        update_identification_type(db, 1, IdentificationTypeUpdate(person_type="JURIDICA"))


def test_divipola_helpers_and_seed(tmp_path):
    from UsersAPI.domains.clients.models.catalogs import CountryDB, DepartmentDB
    from UsersAPI.domains.clients.seeds.divipola import (
        parsear_coordenada,
        normalizar_codigo,
        seed_divipola,
        validar_fila,
    )

    assert normalizar_codigo("5", 2) == "05"
    assert parsear_coordenada("4,123") == Decimal("4.123")
    assert parsear_coordenada("") is None
    with pytest.raises(ValueError):
        normalizar_codigo("", 2)
    with pytest.raises(ValueError):
        parsear_coordenada("abc")
    with pytest.raises(ValueError):
        validar_fila({"Código Departamento": "05", "Código Municipio": "11"})

    csv_path = tmp_path / "DIVIPOLA.csv"
    headers = [
        "Código Departamento", "Nombre Departamento", "Código Municipio",
        "Nombre Municipio", "Tipo: Municipio / Isla / Área no municipalizada",
        "longitud", "Latitud",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerow({
            "Código Departamento": "5", "Nombre Departamento": "Antioquia",
            "Código Municipio": "5001", "Nombre Municipio": "Medellin",
            "Tipo: Municipio / Isla / Área no municipalizada": "Municipio",
            "longitud": "-75.5", "Latitud": "6.2",
        })

    country = CountryDB(id=1, code="CO", name="Colombia", active=True)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.side_effect = [country, None, None]
    result = seed_divipola(db, csv_path)
    assert result["filas"] == 1
    assert result["departamentos_creados"] == 1
    assert result["ciudades_creadas"] == 1


def test_product_image_service_success_and_errors():
    from UsersAPI.domains.inventory.services import product_image_service as service

    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(HTTPException) as exc:
            service.search_product_images("café")
        assert exc.value.status_code == 503

    response = MagicMock()
    response.json.return_value = {
        "photos": [
            {"id": 1, "src": {"medium": "https://img/1"}, "url": "https://p/1", "photographer": "A", "alt": "A"},
            {"id": 2, "src": {}, "url": "https://p/2"},
        ]
    }
    with patch.dict("os.environ", {"PEXELS_API_KEY": "key"}):
        with patch.object(service.requests, "get", return_value=response) as get:
            result = service.search_product_images("  café  ", 99)
    assert result[0]["id"] == 1
    assert get.call_args.kwargs["params"]["per_page"] == 20

    error_response = MagicMock()
    with patch.dict("os.environ", {"PEXELS_API_KEY": "key"}):
        with patch.object(service.requests, "get", side_effect=service.requests.RequestException("boom")):
            with pytest.raises(HTTPException) as exc:
                service.search_product_images("café")
    assert exc.value.status_code == 502


def test_screening_bulk_sync_success_duplicate_missing_and_error():
    from UsersAPI.domains.clients.services import screening_bulk_sync_service as service

    source = SimpleNamespace(id=10, name="Fuente", url="https://example", last_sync_at=None, last_sync_status=None, last_sync_error=None)
    response = MagicMock(content=b"xml", status_code=200)
    parsed = [
        {"external_id": "1", "entry_type": "SDN", "name": "John", "aliases": [], "identification_numbers": [], "raw_data": {}},
        {"external_id": "1", "entry_type": "SDN", "name": "John dup", "aliases": [], "identification_numbers": [], "raw_data": {}},
    ]
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [("2",)]
    db.execute.return_value.rowcount = 1
    with patch.object(service, "_get_source", return_value=source), patch.object(service.requests, "get", return_value=response), patch.object(service, "_parse_source", return_value=parsed), patch.object(service, "normalize_screening_text", return_value="JOHN"):
        result = service._sync_source_bulk(db, "OFAC_SDN")
    assert result["status"] == "SUCCESS"
    assert result["created"] == 1
    assert result["updated"] == 0
    assert result["deactivated"] == 1
    assert source.last_sync_status == "SUCCESS"

    with patch.object(service, "_get_source", return_value=source), patch.object(service.requests, "get", side_effect=RuntimeError("network")):
        with pytest.raises(RuntimeError):
            service._sync_source_bulk(db, "OFAC_SDN")
    assert source.last_sync_status == "ERROR"

    with patch.object(service, "_sync_source_bulk", side_effect=[{"source": "A", "status": "SUCCESS"}, RuntimeError("x")]):
        with patch.object(service, "SCREENING_LIST_PROVIDERS", ["A", "B"]):
            result = service.sync_all_screening_lists_bulk(db)
    assert result["status"] == "PARTIAL_ERROR"
    assert result["successful_sources"] == 1
    assert result["failed_sources"] == 1


def test_screening_sync_job_skip_and_lock_paths():
    from UsersAPI.domains.clients.services import screening_sync_job as job

    with patch.object(job, "ENABLED", False):
        assert job.run_restrictive_lists_sync_job() == {"status": "skipped", "reason": "sync_disabled"}

    class FakeDateTime:
        @classmethod
        def now(cls, tz):
            return datetime(2026, 9, 8, 6, 0, tzinfo=tz)

        @classmethod
        def combine(cls, d, t, tzinfo=None):
            return datetime.combine(d, t, tzinfo=tzinfo)

    with patch.object(job, "ENABLED", True), patch.object(job, "RUN_TIME", "07:00"), patch.object(job, "datetime", FakeDateTime):
        result = job.run_restrictive_lists_sync_job("TEST")
    assert result["reason"] == "before_configured_time"

    db = MagicMock()
    db.execute.return_value.scalar.return_value = False
    with patch.object(job, "ENABLED", True), patch.object(job, "RUN_TIME", "00:00"), patch.object(job, "SessionLocal", return_value=db), patch.object(job.datetime, "now", return_value=datetime(2026, 9, 8, 10, 0, tzinfo=job.ZoneInfo(job.TIMEZONE))):
        result = job.run_restrictive_lists_sync_job()
    assert result["reason"] == "another_instance_is_running"
    db.close.assert_called_once()


def test_inventory_movement_helpers_and_list_paths():
    from UsersAPI.domains.inventory.schemas import InventoryMovementCreate
    from UsersAPI.domains.inventory.services import inventory_movement_service as service

    assert service._actor_name(SimpleNamespace(email="a")) == "a"
    assert service._actor_name(SimpleNamespace(username="u")) == "u"
    assert service._actor_name(None) == "system"
    assert service._calculate_weighted_average_cost(Decimal("0"), None, Decimal("2"), Decimal("10")) == Decimal("10")
    assert service._calculate_weighted_average_cost(Decimal("2"), Decimal("10"), Decimal("2"), Decimal("20")) == Decimal("15")
    assert service._calculate_reversed_average_cost(Decimal("2"), Decimal("10"), Decimal("2"), Decimal("10"), Decimal("0")) is None
    assert service._calculate_reversed_average_cost(Decimal("2"), None, Decimal("1"), Decimal("10"), Decimal("1")) is None

    base = dict(product_id=1, movement_type="ENTRY", origin_type="PURCHASE", quantity=Decimal("1"), unit_purchase_price=Decimal("10"))
    with pytest.raises(HTTPException):
        service._validate_origin(InventoryMovementCreate(**{**base, "movement_type": "EXIT"}), "PURCHASE", None)
    with pytest.raises(HTTPException):
        service._validate_origin(InventoryMovementCreate(**base), "PURCHASE", uuid4())
    with pytest.raises(HTTPException):
        service._validate_origin(InventoryMovementCreate(**base), "REVERSAL", None)

    with patch.object(service.InventoryMovementRepository, "list_all", return_value=[]), patch.object(service.InventoryMovementRepository, "list_by_product", return_value=[MagicMock()]):
        db = MagicMock()
        assert service.list_inventory_movements(db, 1) == []
        assert len(service.list_inventory_movements(db, 1, 2, from_date=date(2026, 1, 1), to_date=date(2026, 1, 2))) == 1
    with pytest.raises(HTTPException):
        service.list_inventory_movements(MagicMock(), 1, from_date=date(2026, 2, 1), to_date=date(2026, 1, 1))

    movement = MagicMock()
    with patch.object(service.InventoryMovementRepository, "get_by_id", return_value=movement):
        assert service.get_inventory_movement(MagicMock(), 1, uuid4()) is movement
    with patch.object(service.InventoryMovementRepository, "get_by_id", return_value=None):
        with pytest.raises(HTTPException):
            service.get_inventory_movement(MagicMock(), 1, uuid4())


def test_inventory_movement_create_and_reverse_paths():
    from UsersAPI.domains.inventory.schemas import InventoryMovementCreate
    from UsersAPI.domains.inventory.services import inventory_movement_service as service

    product = SimpleNamespace(active=True)
    inventory = SimpleNamespace(quantity=Decimal("5"), purchase_price=Decimal("10"), profit_percentage=Decimal("0.2"))
    movement = MagicMock(id=uuid4())
    db = MagicMock()
    with patch.object(service.ProductRepository, "get_by_id", return_value=product), patch.object(service.InventoryRepository, "get_by_product", return_value=inventory), patch.object(service.InventoryRepository, "save"), patch.object(service.InventoryMovementRepository, "add", return_value=movement):
        data = InventoryMovementCreate(product_id=1, movement_type="ENTRY", origin_type="PURCHASE", quantity=Decimal("2"), unit_purchase_price=Decimal("20"), profit_percentage=Decimal("0.3"), notes=" test ")
        result = service.create_inventory_movement(data, db, 1, SimpleNamespace(email="u"))
    assert result is movement
    assert inventory.quantity == Decimal("7")
    assert inventory.purchase_price == Decimal("12.85714285714285714285714286")

    original = SimpleNamespace(id=uuid4(), origin_type="PURCHASE", reversal_of_id=None, quantity=Decimal("2"), movement_type="ENTRY", product_id=1, unit_purchase_price=Decimal("20"), profit_percentage=Decimal("0.3"))
    db.query.return_value.filter.return_value.scalar.return_value = Decimal("0")
    with patch.object(service.InventoryMovementRepository, "get_by_id", return_value=original), patch.object(service, "create_inventory_movement", return_value=movement) as create:
        result = service.reverse_inventory_movement(original.id, db, 1, SimpleNamespace(email="u"), Decimal("1"))
    assert result is movement
    create.assert_called_once()


def test_inventory_controller_delegates_and_handles_reversal_rows():
    from UsersAPI.domains.inventory.controllers import movement_controller as controller
    movement_id = uuid4()
    db = MagicMock()
    current = SimpleNamespace()
    data = MagicMock()
    with patch.object(controller, "create_inventory_movement", return_value="created") as fn:
        assert controller.create_movement(data, db, 1, current) == "created"
        fn.assert_called_once_with(data, db, 1, current)
    with patch.object(controller, "reverse_inventory_movement", return_value="reversed") as fn:
        assert controller.reverse_movement(movement_id, Decimal("1"), db, 1, current) == "reversed"
    with patch.object(controller, "get_inventory_movement", return_value="one"):
        assert controller.get_movement(movement_id, db, 1) == "one"
    with patch.object(controller, "export_movements_excel", return_value="excel"):
        assert controller.export_movements(db, 1) == "excel"

    first = SimpleNamespace(id=uuid4(), origin_type="PURCHASE")
    second = SimpleNamespace(id=uuid4(), origin_type="REVERSAL")
    db.query.return_value.filter.return_value.group_by.return_value.all.return_value = [(first.id, 1)]
    with patch.object(controller, "list_inventory_movements", return_value=[first, second]):
        result = controller.list_movements(None, db, 1)
    assert result[0].reversed_quantity == Decimal("1")
    assert result[1].reversed_quantity == Decimal("0")


def test_inventory_export_paths():
    from UsersAPI.domains.inventory.services import inventory_export_service as service

    db = MagicMock()
    query = MagicMock()
    query.options.return_value = query
    query.join.return_value = query
    query.filter.return_value = query
    query.order_by.return_value = query
    query.all.return_value = []
    db.query.return_value = query
    response = service.export_inventory_excel(db, 1, search="prod", inventory_type_id=2)
    assert response.media_type.startswith("application/vnd.openxmlformats")

    product = SimpleNamespace(code="P1", name="Producto", inventory_type=SimpleNamespace(name="Tipo"))
    movement = SimpleNamespace(
        created_at=datetime(2026, 1, 1, 10, 0), movement_type="ENTRY", origin_type="PURCHASE",
        product=product, quantity=Decimal("2"), unit_purchase_price=Decimal("10"),
        balance_before=Decimal("0"), balance_after=Decimal("2"), id=uuid4(), reversal_of_id=None, notes=None,
    )
    query.all.return_value = [movement]
    response = service.export_movements_excel(db, 1, product_id=1, from_date=date(2026, 1, 1), to_date=date(2026, 1, 2))
    assert response.media_type.startswith("application/vnd.openxmlformats")
    with pytest.raises(ValueError):
        service.export_movements_excel(db, 1, from_date=date(2026, 2, 1), to_date=date(2026, 1, 1))


def test_portfolio_controller_and_routes_delegate_all_paths():
    from UsersAPI.domains.portfolio.controllers import portfolio_controller as controller
    from UsersAPI.domains.portfolio.routes.portfolio_routes import portfolio_routes

    client_id = uuid4()
    db = MagicMock()
    user = SimpleNamespace(tenant_id=7)
    data = MagicMock()
    with patch.object(controller, "get_client_credit", return_value="credit"), patch.object(controller, "upsert_client_credit_limit", return_value="updated"), patch.object(controller, "list_obligations", return_value="obs"), patch.object(controller, "list_client_obligations", return_value="clientobs"), patch.object(controller, "register_payment", return_value="payment"), patch.object(controller, "list_payments", return_value="payments"):
        assert controller.client_credit(client_id, db, 7) == "credit"
        assert controller.update_client_credit(client_id, data, db, 7, user) == "updated"
        assert controller.obligations(db, 7) == "obs"
        assert controller.client_obligations(client_id, db, 7) == "clientobs"
        assert controller.create_payment(data, db, 7, user) == "payment"
        assert controller.payments(db, 7, client_id) == "payments"

    def route(path, method):
        return next(r for r in portfolio_routes.routes if r.path == path and method in r.methods)

    with patch("UsersAPI.domains.portfolio.routes.portfolio_routes.client_credit", return_value="c"):
        assert asyncio.run(route("/portfolio/clients/{client_id}/credit-limit", "GET").endpoint(client_id, db, user)) == "c"
    with patch("UsersAPI.domains.portfolio.routes.portfolio_routes.update_client_credit", return_value="u"):
        assert asyncio.run(route("/portfolio/clients/{client_id}/credit-limit", "PUT").endpoint(client_id, data, db, user, user)) == "u"
    with patch("UsersAPI.domains.portfolio.routes.portfolio_routes.obligations", return_value="all"):
        assert asyncio.run(route("/portfolio/obligations", "GET").endpoint(None, db, user)) == "all"
    with patch("UsersAPI.domains.portfolio.routes.portfolio_routes.client_obligations", return_value="one"):
        assert asyncio.run(route("/portfolio/obligations", "GET").endpoint(client_id, db, user)) == "one"
        assert asyncio.run(route("/portfolio/clients/{client_id}/obligations", "GET").endpoint(client_id, db, user)) == "one"
    with patch("UsersAPI.domains.portfolio.routes.portfolio_routes.create_payment", return_value="p"):
        assert asyncio.run(route("/portfolio/payments", "POST").endpoint(data, db, user, user)) == "p"
    with patch("UsersAPI.domains.portfolio.routes.portfolio_routes.payments", return_value="ps"):
        assert asyncio.run(route("/portfolio/payments", "GET").endpoint(client_id, db, user)) == "ps"


def test_sales_controller_delegates():
    from UsersAPI.domains.sales.controllers import sale_controller as controller
    data = MagicMock()
    db = MagicMock()
    user = MagicMock()
    sale_id = uuid4()
    with patch.object(controller, "create_sale", return_value="c") as fn:
        assert controller.create(data, db, 1, user) == "c"
        fn.assert_called_once_with(data, db, 1, user)
    with patch.object(controller, "get_sale", return_value="g"):
        assert controller.get(sale_id, db, 1) == "g"
    with patch.object(controller, "list_sales", return_value="l"):
        assert controller.list_all(db, 1, 5, 2) == "l"


def test_sales_service_helpers_and_cash_sale():
    from UsersAPI.domains.inventory.models import InventoryDB
    from UsersAPI.domains.sales.schemas import SaleCreate, SaleItemCreate, SalePaymentCreate
    from UsersAPI.domains.sales.services import sale_service as service

    assert service._money(Decimal("10.5")) == Decimal("11")
    assert service._actor_name(SimpleNamespace(email="e")) == "e"
    inventory = SimpleNamespace(quantity=1, purchase_price=Decimal("10"), profit_percentage=Decimal("0.1"))
    assert service._sale_price(inventory) == Decimal("11")
    with pytest.raises(HTTPException):
        service._sale_price(SimpleNamespace(quantity=0, purchase_price=Decimal("10"), profit_percentage=0))

    client = SimpleNamespace(status="INACTIVE", is_listed=False, compliance_status="CLEAR", id=uuid4())
    assert service._client_is_eligible_for_sale(client, MagicMock(), 1) is False
    client.status = "ACTIVE"
    client.is_listed = True
    with patch.object(service, "has_compliance_override", return_value=True):
        assert service._client_is_eligible_for_sale(client, MagicMock(), 1) is True

    product = SimpleNamespace(id=1, code="P1", name="Producto", active=True)
    inventory = SimpleNamespace(quantity=5, purchase_price=Decimal("10"), profit_percentage=Decimal("0"))
    sale = MagicMock()
    sale.items = []
    sale.customers = []
    sale.payments = []
    repo = MagicMock()
    repo.next_sale_number.return_value = "V-1"
    repo.get_by_id.return_value = sale
    db = MagicMock()
    db.scalar.side_effect = [inventory, product]
    db.flush.return_value = None
    data = SaleCreate(
        items=[SaleItemCreate(product_id=1, quantity=Decimal("1"))],
        payments=[SalePaymentCreate(payment_method="EFECTIVO", amount=Decimal("10"))],
    )
    with patch.object(service, "SaleRepository", return_value=repo), patch.object(service, "create_inventory_movement"):
        result = service.create_sale(data, db, 1, SimpleNamespace(email="u"))
    assert result is sale

    with pytest.raises(HTTPException):
        service.create_sale(data.model_copy(update={"items": [data.items[0], data.items[0]]}), MagicMock(), 1, SimpleNamespace(email="u"))


def test_invoice_service_pdf_and_email_paths():
    from UsersAPI.domains.sales.services import invoice_service as service

    sale = SimpleNamespace(
        sale_number="V-1", status="COMPLETED", created_at=datetime(2026, 1, 1, 10, 0),
        items=[SimpleNamespace(product_code="P1", product_name="Producto", quantity=1, unit_price=Decimal("10"), line_total=Decimal("10"))],
        subtotal=Decimal("10"), discount_percentage=Decimal("0"), discount_amount=Decimal("0"), total=Decimal("10"),
        customers=[SimpleNamespace(client_id=uuid4(), customer_name="Cliente", allocation_percentage=Decimal("100"), allocation_amount=Decimal("10"))],
        payments=[SimpleNamespace(payment_method="EFECTIVO", amount=Decimal("10"))],
    )
    pdf = service._invoice_pdf(sale)
    assert pdf.startswith(b"%PDF")

    db = MagicMock()
    with patch.object(service, "get_sale", return_value=sale), patch.object(service.TenantRepository, "get_by_id", return_value=SimpleNamespace(slug="tenant", name="Tenant")), patch.object(service, "send_email"):
        db.scalars.return_value.all.return_value = [SimpleNamespace(email="a@example.com")]
        assert service.send_invoice_email(sale.items[0].product_code if False else uuid4(), db, 1) == ["a@example.com"]

    sale_no_customer = SimpleNamespace(customers=[])
    with patch.object(service, "get_sale", return_value=sale_no_customer):
        with pytest.raises(HTTPException) as exc:
            service.send_invoice_email(uuid4(), db, 1)
    assert exc.value.status_code == 409
