from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException


def test_sale_service_validation_and_helpers():
    from UsersAPI.domains.sales.schemas import SaleCreate
    from UsersAPI.domains.sales.services import sale_service as service

    db = MagicMock()
    user = SimpleNamespace(email="user@example.com")
    client_id = uuid4()

    duplicate = SaleCreate(
        items=[{"product_id": 1, "quantity": 1}, {"product_id": 1, "quantity": 1}],
        payments=[{"payment_method": "EFECTIVO", "amount": 10}],
    )
    with pytest.raises(HTTPException, match="cannot appear more than once"):
        service.create_sale(duplicate, db, 1, user)

    mixed_credit = SaleCreate(
        items=[{"product_id": 1, "quantity": 1}],
        customers=[{"client_id": client_id, "allocation_percentage": 100}],
        payments=[
            {"payment_method": "CREDITO", "amount": 5},
            {"payment_method": "EFECTIVO", "amount": 5},
        ],
    )
    with pytest.raises(HTTPException, match="single CREDITO"):
        service.create_sale(mixed_credit, db, 1, user)

    generic_credit = SaleCreate(
        items=[{"product_id": 1, "quantity": 1}],
        customers=[{"allocation_percentage": 100, "is_generic": True}],
        payments=[{"payment_method": "CREDITO", "amount": 10}],
    )
    with pytest.raises(HTTPException, match="registered client"):
        service.create_sale(generic_credit, db, 1, user)

    client = SimpleNamespace(
        id=client_id,
        status="ACTIVE",
        is_listed=False,
        compliance_status="MATCH",
    )
    with patch.object(service, "has_compliance_override", return_value=False):
        assert service._client_is_eligible_for_sale(client, db, 1) is False

    client.compliance_status = "CLEAR"
    assert service._client_is_eligible_for_sale(client, db, 1) is True

    db.scalar.side_effect = [None]
    with pytest.raises(HTTPException, match="active credit limit"):
        service._credit_available(client_id, db, 1)

    credit = SimpleNamespace(approved_limit=Decimal("100"))
    db.scalar.side_effect = [credit, Decimal("35")]
    assert service._credit_available(client_id, db, 1) == Decimal("65")


def test_sale_service_customer_and_payment_validation():
    from UsersAPI.domains.sales.schemas import SaleCreate
    from UsersAPI.domains.sales.services import sale_service as service

    db = MagicMock()
    user = SimpleNamespace(email="user@example.com")
    client_id = uuid4()
    inventory = SimpleNamespace(
        quantity=1, purchase_price=Decimal("10"), profit_percentage=Decimal("0")
    )
    product = SimpleNamespace(id=1, code="P1", name="Product", active=True)

    generic_with_client = SaleCreate(
        items=[{"product_id": 1, "quantity": 1}],
        customers=[
            {
                "client_id": client_id,
                "allocation_percentage": 100,
                "is_generic": True,
            }
        ],
        payments=[{"payment_method": "EFECTIVO", "amount": 10}],
    )
    with patch.object(service.SaleRepository, "next_sale_number", return_value="V-1"):
        db.scalar.side_effect = [inventory, product]
        with pytest.raises(HTTPException, match="Generic customer"):
            service.create_sale(generic_with_client, db, 1, user)

    invalid_customer = SaleCreate(
        items=[{"product_id": 1, "quantity": 1}],
        customers=[{"allocation_percentage": 100}],
        payments=[{"payment_method": "EFECTIVO", "amount": 10}],
    )
    with patch.object(service.SaleRepository, "next_sale_number", return_value="V-2"):
        db.scalar.side_effect = [inventory, product]
        with pytest.raises(HTTPException, match="client_id or be generic"):
            service.create_sale(invalid_customer, db, 1, user)


def test_sale_service_get_and_list_paths():
    from UsersAPI.domains.sales.services import sale_service as service

    sale_id = uuid4()
    sale = SimpleNamespace(id=sale_id)
    db = MagicMock()
    with patch.object(service.SaleRepository, "get_by_id", return_value=sale):
        assert service.get_sale(sale_id, db, 1) is sale
    with patch.object(service.SaleRepository, "get_by_id", return_value=None):
        with pytest.raises(HTTPException, match="Sale not found"):
            service.get_sale(sale_id, db, 1)
    with patch.object(service.SaleRepository, "list", return_value=[sale]) as listing:
        assert service.list_sales(db, 1, limit=10, offset=2) == [sale]
        listing.assert_called_once_with(1, limit=10, offset=2)


def test_screening_sync_job_success_and_already_done():
    from UsersAPI.domains.clients.services import screening_sync_job as job

    now = datetime(2026, 9, 8, 8, 0)
    execution = SimpleNamespace(
        id=uuid4(),
        status="SUCCESS",
        trigger_type="MANUAL",
        duration_ms=12,
        total_sources=2,
        successful_sources=2,
        failed_sources=0,
    )
    db = MagicMock()
    db.execute.return_value.scalar.return_value = True

    with (
        patch.object(job, "ENABLED", True),
        patch.object(job, "datetime") as dt,
        patch.object(job, "SessionLocal", return_value=db),
        patch.object(job, "_already_succeeded_today", return_value=False),
        patch.object(job, "create_sync_execution", return_value=execution),
        patch.object(job, "run_sync_execution"),
    ):
        dt.now.return_value = now.replace(tzinfo=job.ZoneInfo(job.TIMEZONE))
        result = job.run_restrictive_lists_sync_job("MANUAL")
    assert result["status"] == "SUCCESS"
    assert result["execution_id"] == str(execution.id)
    assert db.close.called

    db2 = MagicMock()
    with (
        patch.object(job, "ENABLED", True),
        patch.object(job, "datetime") as dt,
        patch.object(job, "SessionLocal", return_value=db2),
        patch.object(job, "_already_succeeded_today", return_value=True),
    ):
        dt.now.return_value = now.replace(tzinfo=job.ZoneInfo(job.TIMEZONE))
        result = job.run_restrictive_lists_sync_job("SCHEDULED")
    assert result["reason"] == "already_succeeded_today"


def test_screening_sync_job_unlock_error_and_helpers():
    from UsersAPI.domains.clients.services import screening_sync_job as job

    now = datetime(2026, 9, 8, 8, 0, tzinfo=job.ZoneInfo(job.TIMEZONE))
    assert job._scheduled_target(now).hour == int(job.RUN_TIME.split(":")[0])
    start, end = job._utc_day_bounds(now)
    assert end > start

    execution = SimpleNamespace(
        id=uuid4(),
        status="SUCCESS",
        trigger_type="MANUAL",
        duration_ms=1,
        total_sources=1,
        successful_sources=1,
        failed_sources=0,
    )
    db = MagicMock()
    db.execute.side_effect = [SimpleNamespace(scalar=lambda: True), Exception("unlock")]
    with (
        patch.object(job, "ENABLED", True),
        patch.object(job, "datetime") as dt,
        patch.object(job, "SessionLocal", return_value=db),
        patch.object(job, "_already_succeeded_today", return_value=False),
        patch.object(job, "create_sync_execution", return_value=execution),
        patch.object(job, "run_sync_execution"),
    ):
        dt.now.return_value = now
        result = job.run_restrictive_lists_sync_job("MANUAL")
    assert result["status"] == "SUCCESS"
    assert db.close.called
