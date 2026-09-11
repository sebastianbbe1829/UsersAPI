from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from UsersAPI.domains.cash.services.cash_day_report_service import (
    _fmt_dt,
    build_day_report,
    excel_report,
    pdf_report,
)


def _day():
    return SimpleNamespace(
        id=10,
        tenant_id=1,
        business_date=date(2026, 9, 10),
        status="CLOSED",
        opened_at=datetime(2026, 9, 10, 8, 30, 0),
        closed_at=datetime(2026, 9, 10, 17, 45, 15),
    )


def _register(register_id, box_id, base, status="CLOSED"):
    return SimpleNamespace(
        id=register_id,
        branch_id=4,
        cash_box_id=box_id,
        status=status,
        opening_amount=Decimal(str(base)),
        opened_at=datetime(2026, 9, 10, 8, 30, 0),
        closed_at=(
            datetime(2026, 9, 10, 17, 45, 15)
            if status == "CLOSED"
            else None
        ),
        expected_cash=Decimal("150000.00") if register_id == 1 else Decimal("0"),
        counted_cash=Decimal("150000.00") if register_id == 1 else Decimal("0"),
        difference=Decimal("0.00"),
    )


def _movement(register_id, amount, method, origin, movement_type="INCOME"):
    return SimpleNamespace(
        cash_register_id=register_id,
        amount=Decimal(str(amount)),
        payment_method=method,
        origin_type=origin,
        movement_type=movement_type,
        id=register_id,
    )


def _db():
    db = MagicMock()
    registers = [_register(1, 1, 100000), _register(2, 2, 0)]
    branches = [SimpleNamespace(id=4, name="Caldas Parque")]
    boxes = [SimpleNamespace(id=1, name="Caja 1"), SimpleNamespace(id=2, name="Caja 2")]
    movements = [
        _movement(1, 50000, "EFECTIVO", "SALE"),
        _movement(1, 50000, "TARJETA", "SALE"),
        _movement(1, 50000, "EFECTIVO", "PORTFOLIO_PAYMENT"),
    ]

    db.scalar.return_value = _day()
    db.scalars.side_effect = [
        MagicMock(all=MagicMock(return_value=registers)),
        MagicMock(all=MagicMock(return_value=branches)),
        MagicMock(all=MagicMock(return_value=boxes)),
        MagicMock(all=MagicMock(return_value=movements)),
    ]
    db.execute.side_effect = [
        MagicMock(all=MagicMock(return_value=[
            ("EFECTIVO", Decimal("50000")),
            ("TARJETA", Decimal("50000")),
        ])),
        MagicMock(all=MagicMock(return_value=[
            ("EFECTIVO", Decimal("50000"), "APLICADO"),
        ])),
    ]
    return db


def test_report_uses_one_calculation_for_totals_and_renderers():
    report = build_day_report(
        _db(),
        1,
        10,
        tenant_name="Desarrollo",
        generated_by="cash@test.local",
        generated_at=datetime(2026, 9, 10, 21, 11, 37),
    )

    assert report["total_base"] == Decimal("100000.00")
    assert report["total_expected"] == Decimal("200000.00")
    assert report["total_counted"] == Decimal("150000.00")
    assert report["total_difference"] == Decimal("0.00")
    assert report["cash_sales"] == Decimal("50000.00")
    assert report["cash_payments"] == Decimal("50000.00")
    assert report["sales_by_box_totals"]["Efectivo"] == Decimal("50000.00")
    assert report["sales_by_box_totals"]["Tarjeta"] == Decimal("50000.00")
    assert report["payments_by_box_totals"]["Efectivo"] == Decimal("50000.00")

    xlsx_bytes, xlsx_name = excel_report(report)
    pdf_bytes, pdf_name = pdf_report(report)

    assert xlsx_name == "cierre_caja_2026-09-10.xlsx"
    assert pdf_name == "cierre_caja_2026-09-10.pdf"
    assert xlsx_bytes[:2] == b"PK"
    assert pdf_bytes.startswith(b"%PDF")


def test_report_dates_use_colombia_24_hour_format():
    value = datetime(2026, 9, 10, 21, 11, 37)

    assert _fmt_dt(value) == "10/09/2026 21:11:37"
