from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from UsersAPI.domains.portfolio.models import PaymentDB
from UsersAPI.domains.sales.models import SaleDB, SalePaymentDB

from ..models import BranchDB, CashBoxDB, CashDayDB, CashMovementDB, CashRegisterDB

ZERO = Decimal("0.00")
CASH = {"CASH", "EFECTIVO"}
PREFERRED_METHODS = [
    "Efectivo",
    "Transferencias",
    "PSE",
    "Tarjeta",
    "Crédito",
]
COLOMBIA_TZ = ZoneInfo("America/Bogota")


def _money(value):
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _method(value):
    method = (value or "OTRO").strip().upper()
    if method in CASH:
        return "Efectivo"
    if method in {"TRANSFER", "TRANSFERENCIA", "BANK_TRANSFER"}:
        return "Transferencias"
    if method in {"CARD", "TARJETA", "CREDIT_CARD", "DEBIT_CARD"}:
        return "Tarjeta"
    if method in {"CREDIT", "CREDITO", "CRÉDITO"}:
        return "Crédito"
    if method == "PSE":
        return "PSE"
    return method.title()


def _ordered_methods(sales_day, payments_day):
    available = set(sales_day) | set(payments_day)
    ordered = [method for method in PREFERRED_METHODS if method in available]
    extras = sorted(available - set(PREFERRED_METHODS))
    return ordered + extras


def _to_colombia_datetime(value):
    """Normalize report timestamps to Colombia without shifting naive DB values."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=COLOMBIA_TZ)
    return value.astimezone(COLOMBIA_TZ)


def _fmt_dt(value, empty="—"):
    value = _to_colombia_datetime(value)
    return value.strftime("%d/%m/%Y %H:%M:%S") if value else empty


def _signed_amount(movement):
    amount = _money(movement.amount)
    return amount if movement.movement_type == "INCOME" else -amount


def _result(row):
    if row["difference"] is None:
        return "PENDIENTE"
    return "OK" if row["difference"] == ZERO else "DESCUADRADA"


def _sum_method_rows(rows, key, methods):
    totals = {method: ZERO for method in methods}
    for row in rows:
        for method in methods:
            totals[method] += row[key].get(method, ZERO)
    return totals


def _sum_rows(rows, key):
    return sum((row[key] for row in rows), ZERO)


def _cash_movement_totals(rows):
    totals = {
        "sales_cash": ZERO,
        "payments_cash": ZERO,
        "manual_income": ZERO,
        "manual_expense": ZERO,
        "net_cash": ZERO,
    }
    for row in rows:
        totals["sales_cash"] += row["cash_sales"]
        totals["payments_cash"] += row["cash_payments"]
        totals["manual_income"] += row["manual_income"]
        totals["manual_expense"] += row["manual_expense"]
        totals["net_cash"] += row["net_cash"]
    return totals


def build_day_report(
    db: Session,
    tenant_id: int,
    day_id: int,
    *,
    tenant_name: str | None = None,
    generated_by: str | None = None,
    generated_at: datetime | None = None,
) -> dict:
    """Build the single source of truth consumed by both report renderers."""
    day = db.scalar(
        select(CashDayDB).where(
            CashDayDB.tenant_id == tenant_id,
            CashDayDB.id == day_id,
        )
    )
    if day is None:
        raise ValueError("Día operativo no encontrado.")

    registers = db.scalars(
        select(CashRegisterDB)
        .where(
            CashRegisterDB.tenant_id == tenant_id,
            CashRegisterDB.cash_day_id == day.id,
        )
        .order_by(CashRegisterDB.branch_id, CashRegisterDB.id)
    ).all()
    branches = {
        branch.id: branch.name
        for branch in db.scalars(
            select(BranchDB).where(BranchDB.tenant_id == tenant_id)
        ).all()
    }
    boxes = {
        box.id: box.name
        for box in db.scalars(
            select(CashBoxDB).where(CashBoxDB.tenant_id == tenant_id)
        ).all()
    }
    movements = db.scalars(
        select(CashMovementDB)
        .where(
            CashMovementDB.tenant_id == tenant_id,
            CashMovementDB.business_date == day.business_date,
        )
        .order_by(CashMovementDB.cash_register_id, CashMovementDB.id)
    ).all()

    sales_by_box = defaultdict(lambda: defaultdict(lambda: ZERO))
    payments_by_box = defaultdict(lambda: defaultdict(lambda: ZERO))
    cash_by_register = defaultdict(
        lambda: {
            "cash_sales": ZERO,
            "cash_payments": ZERO,
            "manual_income": ZERO,
            "manual_expense": ZERO,
            "net_cash": ZERO,
        }
    )
    cash_sales = ZERO
    cash_payments = ZERO
    cash_sales_reversals = ZERO
    cash_payment_reversals = ZERO

    for movement in movements:
        amount = _money(movement.amount)
        signed = _signed_amount(movement)
        method = _method(movement.payment_method)
        register_cash = cash_by_register[movement.cash_register_id]

        if movement.origin_type == "SALE":
            sales_by_box[movement.cash_register_id][method] += signed
            if method == "Efectivo":
                if movement.movement_type == "INCOME":
                    cash_sales += amount
                    register_cash["cash_sales"] += amount
                else:
                    cash_sales_reversals += amount
                    register_cash["cash_sales"] -= amount
        elif movement.origin_type in {"PORTFOLIO_PAYMENT", "PAYMENT_REVERSAL"}:
            payments_by_box[movement.cash_register_id][method] += signed
            if method == "Efectivo":
                if movement.origin_type == "PORTFOLIO_PAYMENT":
                    cash_payments += amount
                    register_cash["cash_payments"] += amount
                else:
                    cash_payment_reversals += amount
                    register_cash["cash_payments"] -= amount
        elif movement.origin_type == "MANUAL":
            if movement.movement_type == "INCOME":
                register_cash["manual_income"] += amount
            else:
                register_cash["manual_expense"] += amount

        if method == "Efectivo":
            register_cash["net_cash"] += signed

    sale_rows = db.execute(
        select(SalePaymentDB.payment_method, SalePaymentDB.amount)
        .join(SaleDB, SaleDB.id == SalePaymentDB.sale_id)
        .where(
            SalePaymentDB.tenant_id == tenant_id,
            SaleDB.tenant_id == tenant_id,
            SaleDB.business_date == day.business_date,
            SaleDB.status != "CANCELLED",
        )
    ).all()
    sales_day = defaultdict(lambda: ZERO)
    for method, amount in sale_rows:
        sales_day[_method(method)] += _money(amount)

    payment_rows = db.execute(
        select(PaymentDB.payment_method, PaymentDB.amount, PaymentDB.status).where(
            PaymentDB.tenant_id == tenant_id,
            PaymentDB.payment_date == day.business_date,
        )
    ).all()
    payments_day = defaultdict(lambda: ZERO)
    for method, amount, status in payment_rows:
        value = _money(amount)
        payments_day[_method(method)] += value if status == "APLICADO" else -value

    register_rows = []
    total_expected = ZERO
    total_counted = ZERO
    total_difference = ZERO

    for register in registers:
        base_amount = _money(register.opening_amount)
        expected_calculated = base_amount + cash_by_register[register.id]["net_cash"]
        if register.status == "OPEN" or register.expected_cash is None:
            expected = expected_calculated
        else:
            expected = _money(register.expected_cash)

        counted = _money(register.counted_cash) if register.counted_cash is not None else None
        difference = _money(register.difference) if register.difference is not None else None
        total_expected += expected
        if counted is not None:
            total_counted += counted
            total_difference += difference or ZERO

        cash_data = cash_by_register[register.id]
        register_rows.append(
            {
                "register_id": register.id,
                "branch": branches.get(register.branch_id, "—"),
                "box": boxes.get(register.cash_box_id, f"Caja #{register.id}"),
                "status": register.status,
                "base_amount": base_amount,
                "opening_amount": base_amount,
                "opened_at": register.opened_at,
                "closed_at": register.closed_at,
                "expected": expected,
                "counted": counted,
                "difference": difference,
                "sales": dict(sales_by_box[register.id]),
                "payments": dict(payments_by_box[register.id]),
                "cash_sales": cash_data["cash_sales"],
                "cash_payments": cash_data["cash_payments"],
                "manual_income": cash_data["manual_income"],
                "manual_expense": cash_data["manual_expense"],
                "net_cash": cash_data["net_cash"],
            }
        )

    methods = _ordered_methods(sales_day, payments_day)
    sales_by_box_totals = _sum_method_rows(register_rows, "sales", methods)
    payments_by_box_totals = _sum_method_rows(register_rows, "payments", methods)
    cash_movement_totals = _cash_movement_totals(register_rows)

    closed_ok = []
    closed_mismatch = []
    pending = []
    for row in register_rows:
        if row["status"] == "CLOSED" and row["difference"] is not None:
            if row["difference"] == ZERO:
                closed_ok.append(row)
            else:
                closed_mismatch.append(row)
        else:
            pending.append(row)

    generated_at = _to_colombia_datetime(generated_at or datetime.now(COLOMBIA_TZ))
    return {
        "day": day,
        "registers": register_rows,
        "methods": methods,
        "sales_day": dict(sales_day),
        "payments_day": dict(payments_day),
        "sales_by_box_totals": sales_by_box_totals,
        "payments_by_box_totals": payments_by_box_totals,
        "cash_movement_totals": cash_movement_totals,
        "closed_ok": closed_ok,
        "closed_mismatch": closed_mismatch,
        "pending": pending,
        "total_base": _sum_rows(register_rows, "base_amount"),
        "total_opening": _sum_rows(register_rows, "opening_amount"),
        "total_expected": total_expected,
        "total_counted": total_counted,
        "total_difference": total_difference,
        "cash_sales": cash_sales,
        "cash_payments": cash_payments,
        "cash_sales_reversals": cash_sales_reversals,
        "cash_payment_reversals": cash_payment_reversals,
        "tenant_name": tenant_name or "—",
        "generated_by": generated_by or "—",
        "generated_at": generated_at,
    }


def _filename(report, extension):
    return f"cierre_caja_{report['day'].business_date.isoformat()}.{extension}"


def _money_text(value):
    return f"${value:,.0f}"


def excel_report(report) -> tuple[bytes, str]:
    """Render the already-calculated report without performing business calculations."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    ws.append(["RESUMEN CIERRE DE CAJA", None])
    ws.append(["Tenant", report["tenant_name"]])
    ws.append(["Fecha operativa", report["day"].business_date.isoformat()])
    ws.append(["Estado", report["day"].status])
    ws.append(["Generado por", report["generated_by"]])
    ws.append(["Fecha/hora generación", _fmt_dt(report["generated_at"])])
    ws.append(["Apertura del día", _fmt_dt(report["day"].opened_at)])
    ws.append(["Cierre del día", _fmt_dt(report["day"].closed_at, "Pendiente")])
    ws.append([])
    ws.append(["Concepto", "Valor"])
    ws.append(["Total bases", float(report["total_base"])])
    ws.append(["Total aperturas", float(report["total_opening"])])
    ws.append(["Total esperado cajas", float(report["total_expected"])])
    ws.append(["Total contado cajas", float(report["total_counted"])])
    ws.append(["Total diferencia", float(report["total_difference"])])
    ws.append(["Efectivo ventas", float(report["cash_sales"])])
    ws.append(["Efectivo pagos de cartera", float(report["cash_payments"])])
    ws.append(["Reversiones efectivo ventas", float(report["cash_sales_reversals"])])
    ws.append(["Reversiones efectivo pagos", float(report["cash_payment_reversals"])])
    ws.append([])
    ws.append(["VENTAS DEL DÍA POR MEDIO DE PAGO"])
    ws.append(["Medio", "Total"])
    for method in report["methods"]:
        ws.append([method, float(report["sales_day"].get(method, ZERO))])
    ws.append(["TOTAL", float(sum(report["sales_day"].values(), ZERO))])

    wp = wb.create_sheet("Pagos del día")
    wp.append(["MEDIO", "TOTAL PAGOS"])
    for method in report["methods"]:
        wp.append([method, float(report["payments_day"].get(method, ZERO))])
    wp.append(["TOTAL", float(sum(report["payments_day"].values(), ZERO))])

    wc = wb.create_sheet("Ventas por caja")
    wc.append(["Sucursal", "Caja", "Estado", *report["methods"], "Total ventas"])
    for row in report["registers"]:
        values = [row["sales"].get(method, ZERO) for method in report["methods"]]
        wc.append([
            row["branch"],
            row["box"],
            row["status"],
            *map(float, values),
            float(sum(values, ZERO)),
        ])
    wc.append([
        "TOTAL",
        "",
        "",
        *[float(report["sales_by_box_totals"].get(method, ZERO)) for method in report["methods"]],
        float(sum(report["sales_by_box_totals"].values(), ZERO)),
    ])

    wpc = wb.create_sheet("Pagos por caja")
    wpc.append(["Sucursal", "Caja", "Estado", *report["methods"], "Total pagos"])
    for row in report["registers"]:
        values = [row["payments"].get(method, ZERO) for method in report["methods"]]
        wpc.append([
            row["branch"],
            row["box"],
            row["status"],
            *map(float, values),
            float(sum(values, ZERO)),
        ])
    wpc.append([
        "TOTAL",
        "",
        "",
        *[float(report["payments_by_box_totals"].get(method, ZERO)) for method in report["methods"]],
        float(sum(report["payments_by_box_totals"].values(), ZERO)),
    ])

    wa = wb.create_sheet("Arqueos")
    wa.append([
        "Sucursal", "Caja", "Estado", "Base", "Apertura", "Hora apertura",
        "Hora cierre", "Esperado", "Contado", "Diferencia", "Resultado",
    ])
    for row in report["registers"]:
        wa.append([
            row["branch"],
            row["box"],
            row["status"],
            float(row["base_amount"]),
            float(row["opening_amount"]),
            _fmt_dt(row["opened_at"]),
            _fmt_dt(row["closed_at"], "Pendiente"),
            float(row["expected"]),
            None if row["counted"] is None else float(row["counted"]),
            None if row["difference"] is None else float(row["difference"]),
            _result(row),
        ])
    wa.append([
        "TOTAL",
        "",
        "",
        float(report["total_base"]),
        float(report["total_opening"]),
        "",
        "",
        float(report["total_expected"]),
        float(report["total_counted"]),
        float(report["total_difference"]),
        "PENDIENTE" if report["pending"] else ("OK" if not report["closed_mismatch"] else "DESCUADRADA"),
    ])

    wm = wb.create_sheet("Movimientos efectivo")
    wm.append([
        "Caja", "Ventas efectivo", "Pagos efectivo", "Ingresos manuales",
        "Egresos manuales", "Neto efectivo",
    ])
    for row in report["registers"]:
        wm.append([
            row["box"],
            float(row["cash_sales"]),
            float(row["cash_payments"]),
            float(row["manual_income"]),
            float(row["manual_expense"]),
            float(row["net_cash"]),
        ])
    cash_totals = report["cash_movement_totals"]
    wm.append([
        "TOTAL",
        float(cash_totals["sales_cash"]),
        float(cash_totals["payments_cash"]),
        float(cash_totals["manual_income"]),
        float(cash_totals["manual_expense"]),
        float(cash_totals["net_cash"]),
    ])

    for sheet in wb.worksheets:
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for cell in sheet[1]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill(fill_type="solid", fgColor="D9EAF7")
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, float):
                    cell.number_format = "#,##0.00"
        for column in sheet.columns:
            width = min(max(len(str(cell.value or "")) for cell in column) + 2, 35)
            sheet.column_dimensions[column[0].column_letter].width = width

    output = BytesIO()
    wb.save(output)
    return output.getvalue(), _filename(report, "xlsx")


def _pdf_table(rows, align_from=2):
    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAF7")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ALIGN", (align_from, 1), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    return table


def _pdf_method_totals_row(label, methods, totals):
    return [
        label,
        *[_money_text(totals.get(method, ZERO)) for method in methods],
        _money_text(sum(totals.values(), ZERO)),
    ]


def pdf_report(report) -> tuple[bytes, str]:
    """Render the already-calculated report without performing business calculations."""
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )
    styles = getSampleStyleSheet()
    day = report["day"]

    story = [
        Paragraph("Resumen de cierre de Caja", styles["Title"]),
        Paragraph(f"Tenant: {report['tenant_name']}", styles["Normal"]),
        Paragraph(
            f"Fecha operativa: {day.business_date} · Estado: {day.status}",
            styles["Normal"],
        ),
        Paragraph(
            f"Generado por: {report['generated_by']} · "
            f"Generado: {_fmt_dt(report['generated_at'])}",
            styles["Normal"],
        ),
        Paragraph(
            f"Apertura del día: {_fmt_dt(day.opened_at)} · "
            f"Cierre del día: {_fmt_dt(day.closed_at, 'Pendiente')}",
            styles["Normal"],
        ),
        Spacer(1, 5 * mm),
    ]

    summary = [[
        "Total bases", "Total esperado", "Total contado", "Total diferencia",
        "Efectivo ventas", "Efectivo pagos",
    ], [
        _money_text(report["total_base"]),
        _money_text(report["total_expected"]),
        _money_text(report["total_counted"]),
        _money_text(report["total_difference"]),
        _money_text(report["cash_sales"]),
        _money_text(report["cash_payments"]),
    ]]
    story.extend([_pdf_table(summary, align_from=0), Spacer(1, 5 * mm)])

    methods = report["methods"]
    sales_table = [["Caja", "Estado", *methods, "Total"]]
    for row in report["registers"]:
        values = [row["sales"].get(method, ZERO) for method in methods]
        sales_table.append([
            row["box"], row["status"],
            *[_money_text(value) for value in values],
            _money_text(sum(values, ZERO)),
        ])
    sales_table.append(_pdf_method_totals_row("TOTAL", methods, report["sales_by_box_totals"]))
    story.extend([
        Paragraph("Ventas por caja", styles["Heading2"]),
        _pdf_table(sales_table),
        Spacer(1, 5 * mm),
    ])

    payment_table = [["Caja", "Estado", *methods, "Total"]]
    for row in report["registers"]:
        values = [row["payments"].get(method, ZERO) for method in methods]
        payment_table.append([
            row["box"], row["status"],
            *[_money_text(value) for value in values],
            _money_text(sum(values, ZERO)),
        ])
    payment_table.append(_pdf_method_totals_row("TOTAL", methods, report["payments_by_box_totals"]))
    story.extend([
        Paragraph("Pagos de cartera por caja", styles["Heading2"]),
        _pdf_table(payment_table),
        Spacer(1, 5 * mm),
    ])

    cash_totals = report["cash_movement_totals"]
    cash_table = [[
        "Caja", "Ventas efectivo", "Pagos efectivo", "Ingresos manuales",
        "Egresos manuales", "Neto efectivo",
    ]]
    for row in report["registers"]:
        cash_table.append([
            row["box"],
            _money_text(row["cash_sales"]),
            _money_text(row["cash_payments"]),
            _money_text(row["manual_income"]),
            _money_text(row["manual_expense"]),
            _money_text(row["net_cash"]),
        ])
    cash_table.append([
        "TOTAL",
        _money_text(cash_totals["sales_cash"]),
        _money_text(cash_totals["payments_cash"]),
        _money_text(cash_totals["manual_income"]),
        _money_text(cash_totals["manual_expense"]),
        _money_text(cash_totals["net_cash"]),
    ])
    story.extend([
        Paragraph("Movimientos de efectivo", styles["Heading2"]),
        _pdf_table(cash_table, align_from=1),
        Spacer(1, 5 * mm),
    ])

    reconciliation = [[
        "Caja", "Sucursal", "Base", "Apertura", "Hora apertura", "Hora cierre",
        "Esperado", "Contado", "Diferencia", "Resultado",
    ]]
    for row in report["registers"]:
        reconciliation.append([
            row["box"], row["branch"],
            _money_text(row["base_amount"]),
            _money_text(row["opening_amount"]),
            _fmt_dt(row["opened_at"]),
            _fmt_dt(row["closed_at"], "Pendiente"),
            _money_text(row["expected"]),
            "—" if row["counted"] is None else _money_text(row["counted"]),
            "—" if row["difference"] is None else _money_text(row["difference"]),
            _result(row),
        ])
    reconciliation.append([
        "TOTAL", "",
        _money_text(report["total_base"]),
        _money_text(report["total_opening"]),
        "", "",
        _money_text(report["total_expected"]),
        _money_text(report["total_counted"]),
        _money_text(report["total_difference"]),
        "PENDIENTE" if report["pending"] else (
            "OK" if not report["closed_mismatch"] else "DESCUADRADA"
        ),
    ])
    story.extend([
        Paragraph("Arqueos y diferencias", styles["Heading2"]),
        _pdf_table(reconciliation, align_from=2),
        Spacer(1, 4 * mm),
    ])

    if report["pending"]:
        story.append(
            Paragraph(
                f"Cajas pendientes de arqueo: {len(report['pending'])}",
                styles["Normal"],
            )
        )

    total_sales = sum(report["sales_day"].values(), ZERO)
    total_sales_by_box = sum(report["sales_by_box_totals"].values(), ZERO)
    credit_sales = report["sales_day"].get("Crédito", ZERO)
    if credit_sales:
        story.append(
            Paragraph(
                "Ventas a crédito del día (sin movimiento de caja asignable): "
                f"{_money_text(credit_sales)}",
                styles["Normal"],
            )
        )
    if total_sales != total_sales_by_box:
        story.append(
            Paragraph(
                "Diferencia entre ventas del día y ventas asignadas a cajas: "
                f"{_money_text(total_sales - total_sales_by_box)}",
                styles["Normal"],
            )
        )

    total_payments = sum(report["payments_day"].values(), ZERO)
    total_payments_by_box = sum(report["payments_by_box_totals"].values(), ZERO)
    if total_payments != total_payments_by_box:
        story.append(
            Paragraph(
                "Diferencia entre pagos del día y pagos asignados a cajas: "
                f"{_money_text(total_payments - total_payments_by_box)}",
                styles["Normal"],
            )
        )

    doc.build(story)
    return output.getvalue(), _filename(report, "pdf")
