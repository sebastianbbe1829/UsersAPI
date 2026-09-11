from datetime import timezone
from zoneinfo import ZoneInfo

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle
from sqlalchemy import select

from UsersAPI.domains.sales.models import SaleDB, SalePaymentDB

from ..models import CashMovementDB
from . import cash_day_report_service as report_service

COLOMBIA_TZ = ZoneInfo("America/Bogota")
UTC = timezone.utc
_CURRENT_REPORT = None


def _to_colombia_datetime(value):
    """Convert Caja timestamps stored as UTC to Colombia for presentation."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(COLOMBIA_TZ)


def _fmt_dt(value, empty="—"):
    """Render Caja timestamps in Colombian 12-hour format with AM/PM."""
    value = _to_colombia_datetime(value)
    return value.strftime("%d/%m/%Y %I:%M:%S %p") if value else empty


def _normalize_legacy_report_timestamps(report):
    """Keep report timestamps consistent with the UTC storage convention."""
    return report


def _assign_credit_sales_to_registers(report, db, tenant_id):
    """Associate credit sales with their sale register without creating cash movement."""
    day = report.get("day")
    if day is None:
        return

    movements = db.scalars(
        select(CashMovementDB).where(
            CashMovementDB.tenant_id == tenant_id,
            CashMovementDB.business_date == day.business_date,
            CashMovementDB.origin_type == "SALE",
        )
    ).all()

    sale_register = {}
    for movement in movements:
        sale_register.setdefault(str(movement.origin_id), movement.cash_register_id)

    register_rows = {row["register_id"]: row for row in report["registers"]}
    credit_total = report_service._money(
        report["sales_day"].get("Crédito", report_service.ZERO)
    )
    unassigned_credit = credit_total

    credit_rows = db.execute(
        select(SalePaymentDB.sale_id, SalePaymentDB.amount, SalePaymentDB.cash_register_id)
        .join(SaleDB, SaleDB.id == SalePaymentDB.sale_id)
        .where(
            SalePaymentDB.tenant_id == tenant_id,
            SaleDB.tenant_id == tenant_id,
            SaleDB.business_date == day.business_date,
            SaleDB.status != "CANCELLED",
            SalePaymentDB.payment_method.in_(
                ["CREDITO", "CREDIT", "CRÉDITO"]
            ),
        )
    ).all()

    for sale_id, amount, stored_register_id in credit_rows:
        value = report_service._money(amount)
        register_id = stored_register_id or sale_register.get(str(sale_id))
        if register_id is None or register_id not in register_rows:
            continue

        row = register_rows[register_id]
        row["sales"]["Crédito"] = row["sales"].get("Crédito", report_service.ZERO) + value
        report["sales_by_box_totals"]["Crédito"] = (
            report["sales_by_box_totals"].get("Crédito", report_service.ZERO) + value
        )
        unassigned_credit -= value

    report["unassigned_credit_sales"] = max(
        report_service.ZERO,
        report_service._money(unassigned_credit),
    )


def _without_sales_difference_paragraph(text, style, *args, **kwargs):
    """Hide only technical reconciliation text and render the credit legend."""
    if isinstance(text, str) and text.startswith(
        "Diferencia entre ventas del día y ventas asignadas a cajas:"
    ):
        return Spacer(1, 0)

    if isinstance(text, str) and text.startswith("Ventas a crédito del día"):
        unassigned = (
            _CURRENT_REPORT.get("unassigned_credit_sales", report_service.ZERO)
            if _CURRENT_REPORT is not None
            else report_service.ZERO
        )
        if not unassigned:
            return Spacer(1, 0)
        text = (
            "Ventas a crédito del día (sin movimiento de caja asignable): "
            f"{report_service._money_text(unassigned)}"
        )

    return _ORIGINAL_PARAGRAPH(text, style, *args, **kwargs)


report_service._to_colombia_datetime = _to_colombia_datetime
report_service._fmt_dt = _fmt_dt
_ORIGINAL_PARAGRAPH = report_service.Paragraph
_ORIGINAL_DOC = report_service.SimpleDocTemplate
_ORIGINAL_SPACER = report_service.Spacer
_ORIGINAL_SIDE_BY_SIDE = report_service._pdf_side_by_side_payment_tables
_ORIGINAL_PDF_TABLE = report_service._pdf_table


def _compact_pdf_table(rows, align_from=2):
    """Use the same compact table typography throughout the complete PDF."""
    table = _ORIGINAL_PDF_TABLE(rows, align_from=align_from)
    table.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("LEADING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _two_column_layout(left_title, left_table, right_title, right_table, styles, doc_width, *, left_align_from=1, right_align_from=1):
    """Render two titled tables side by side using the same report table styling."""
    column_width = (doc_width - 5 * mm) / 2

    left = [
        _ORIGINAL_PARAGRAPH(left_title, styles["Heading2"]),
        _compact_pdf_table(left_table, align_from=left_align_from),
    ]
    right = [
        _ORIGINAL_PARAGRAPH(right_title, styles["Heading2"]),
        _compact_pdf_table(right_table, align_from=right_align_from),
    ]

    layout = Table(
        [[left, right]],
        colWidths=[column_width, column_width],
        hAlign="LEFT",
    )
    layout.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 2.5 * mm),
                ("LEFTPADDING", (1, 0), (1, 0), 2.5 * mm),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return KeepTogether([layout])


def _proper_side_by_side_payment_tables(sales_table, payments_table, styles, doc_width):
    """Render the narrower portfolio table on the left and sales table on the right."""
    return _two_column_layout(
        "Pagos de cartera del día por medio de pago",
        payments_table,
        "Ventas del día por medio de pago",
        sales_table,
        styles,
        doc_width,
        left_align_from=1,
        right_align_from=1,
    )


def _side_by_side_summary_status(summary, status_table, styles, doc_width):
    """Render the table with fewer columns on the left and the wider summary on the right."""
    return _two_column_layout(
        "Estado de cajas",
        status_table,
        "Resumen de caja",
        summary,
        styles,
        doc_width,
        left_align_from=1,
        right_align_from=0,
    )


def _side_by_side_register_tables(sales_table, payment_table, styles, doc_width):
    """Render payments by box on the left and sales by box on the right."""
    return _two_column_layout(
        "Pagos de cartera por caja",
        payment_table,
        "Ventas por caja",
        sales_table,
        styles,
        doc_width,
        left_align_from=1,
        right_align_from=2,
    )


def build_day_report(*args, **kwargs):
    report = report_service.build_day_report(*args, **kwargs)
    _normalize_legacy_report_timestamps(report)
    db = args[0] if args else kwargs["db"]
    tenant_id = args[1] if len(args) > 1 else kwargs["tenant_id"]
    _assign_credit_sales_to_registers(report, db, tenant_id)
    return report


def excel_report(report):
    _normalize_legacy_report_timestamps(report)
    original_fmt = report_service._fmt_dt
    original_to_colombia = report_service._to_colombia_datetime
    report_service._fmt_dt = _fmt_dt
    report_service._to_colombia_datetime = _to_colombia_datetime
    try:
        return report_service.excel_report(report)
    finally:
        report_service._fmt_dt = original_fmt
        report_service._to_colombia_datetime = original_to_colombia


def _compact_doc(*args, **kwargs):
    """Use landscape A4 with compact margins for the one-page closing report."""
    kwargs.update(
        {
            "rightMargin": 5 * mm,
            "leftMargin": 5 * mm,
            "topMargin": 4 * mm,
            "bottomMargin": 4 * mm,
        }
    )
    return _ORIGINAL_DOC(*args, **kwargs)


def _compact_spacer(width, height):
    """Reduce section gaps without changing report content."""
    return _ORIGINAL_SPACER(width, min(height, 1.5 * mm))


def pdf_report(report):
    """Render the Caja PDF with compact, consistent two-column summary sections."""
    global _CURRENT_REPORT
    _normalize_legacy_report_timestamps(report)

    styles = getSampleStyleSheet()
    day = report["day"]
    section_style = styles["Heading2"]
    output = report_service.BytesIO()
    doc = _compact_doc(
        output,
        pagesize=landscape(A4),
    )

    methods = report["methods"]
    payment_methods = report["payment_methods"]
    sales_day_table = [["Medio", "Total"]]
    for method in methods:
        sales_day_table.append(
            [method, report_service._money_text(report["sales_day"].get(method, report_service.ZERO))]
        )
    sales_day_table.append(
        ["TOTAL", report_service._money_text(sum(report["sales_day"].values(), report_service.ZERO))]
    )

    payments_day_table = [["Medio", "Total"]]
    for method in payment_methods:
        payments_day_table.append(
            [method, report_service._money_text(report["payments_day"].get(method, report_service.ZERO))]
        )
    payments_day_table.append(
        ["TOTAL", report_service._money_text(sum(report["payments_day"].values(), report_service.ZERO))]
    )

    summary = [
        ["Total bases", "Total esperado", "Total contado", "Total diferencia", "Efectivo ventas", "Efectivo pagos"],
        [
            report_service._money_text(report["total_base"]),
            report_service._money_text(report["total_expected"]),
            report_service._money_text(report["total_counted"]),
            report_service._money_text(report["total_difference"]),
            report_service._money_text(report["cash_sales"]),
            report_service._money_text(report["cash_payments"]),
        ],
    ]
    status_table = [
        ["Estado de cajas", "Cantidad"],
        ["OK", str(report["status_totals"]["OK"])],
        ["DESCUADRADA", str(report["status_totals"]["DESCUADRADA"])],
        ["PENDIENTE", str(report["status_totals"]["PENDIENTE"])],
    ]

    sales_table = [["Caja", "Estado", *methods, "Total"]]
    for row in report["registers"]:
        values = [row["sales"].get(method, report_service.ZERO) for method in methods]
        sales_table.append(
            [row["box"], row["status"], *[report_service._money_text(value) for value in values], report_service._money_text(sum(values, report_service.ZERO))]
        )
    sales_table.append(
        report_service._pdf_method_totals_row("TOTAL", methods, report["sales_by_box_totals"])
    )

    payment_table = [["Caja", "Estado", *payment_methods, "Total"]]
    for row in report["registers"]:
        values = [row["payments"].get(method, report_service.ZERO) for method in payment_methods]
        payment_table.append(
            [row["box"], row["status"], *[report_service._money_text(value) for value in values], report_service._money_text(sum(values, report_service.ZERO))]
        )
    payment_table.append(
        report_service._pdf_method_totals_row("TOTAL", payment_methods, report["payments_by_box_totals"])
    )

    cash_totals = report["cash_movement_totals"]
    cash_table = [["Caja", "Ventas efectivo", "Pagos efectivo", "Ingresos manuales", "Egresos manuales", "Neto efectivo"]]
    for row in report["registers"]:
        cash_table.append(
            [row["box"], report_service._money_text(row["cash_sales"]), report_service._money_text(row["cash_payments"]), report_service._money_text(row["manual_income"]), report_service._money_text(row["manual_expense"]), report_service._money_text(row["net_cash"])]
        )
    cash_table.append(
        ["TOTAL", report_service._money_text(cash_totals["sales_cash"]), report_service._money_text(cash_totals["payments_cash"]), report_service._money_text(cash_totals["manual_income"]), report_service._money_text(cash_totals["manual_expense"]), report_service._money_text(cash_totals["net_cash"])]
    )

    reconciliation = [["Caja", "Sucursal", "Base", "Apertura", "Hora apertura", "Hora cierre", "Esperado", "Contado", "Diferencia", "Resultado"]]
    for row in report["registers"]:
        reconciliation.append(
            [row["box"], row["branch"], report_service._money_text(row["base_amount"]), report_service._money_text(row["opening_amount"]), _fmt_dt(row["opened_at"]), _fmt_dt(row["closed_at"], "Pendiente"), report_service._money_text(row["expected"]), "—" if row["counted"] is None else report_service._money_text(row["counted"]), "—" if row["difference"] is None else report_service._money_text(row["difference"]), report_service._result(row)]
        )
    reconciliation.append(
        ["TOTAL", "", report_service._money_text(report["total_base"]), report_service._money_text(report["total_opening"]), "", "", report_service._money_text(report["total_expected"]), report_service._money_text(report["total_counted"]), report_service._money_text(report["total_difference"]), "PENDIENTE" if report["pending"] else ("OK" if not report["closed_mismatch"] else "DESCUADRADA")]
    )

    story = [
        Paragraph("Resumen de cierre de Caja", styles["Title"]),
        Paragraph(f"Tenant: {report['tenant_name']}", styles["Normal"]),
        Paragraph(f"Fecha operativa: {day.business_date} · Estado: {day.status}", styles["Normal"]),
        Paragraph(f"Generado por: {report['generated_by']} · Generado: {_fmt_dt(report['generated_at'])}", styles["Normal"]),
        Paragraph(f"Apertura del día: {_fmt_dt(day.opened_at)} · Cierre del día: {_fmt_dt(day.closed_at, 'Pendiente')}", styles["Normal"]),
        Spacer(1, 1.5 * mm),
        _side_by_side_summary_status(summary, status_table, styles, doc.width),
        Spacer(1, 1.5 * mm),
        _proper_side_by_side_payment_tables(sales_day_table, payments_day_table, styles, doc.width),
        Spacer(1, 1.5 * mm),
        _side_by_side_register_tables(sales_table, payment_table, styles, doc.width),
        Spacer(1, 1.5 * mm),
        Paragraph("Movimientos de efectivo", section_style),
        _compact_pdf_table(cash_table, align_from=1),
        Spacer(1, 1.5 * mm),
        Paragraph("Arqueos y diferencias", section_style),
        _compact_pdf_table(reconciliation, align_from=2),
    ]

    if report.get("unassigned_credit_sales"):
        story.append(
            Paragraph(
                f"Ventas a crédito del día (sin movimiento de caja asignable): {report_service._money_text(report['unassigned_credit_sales'])}",
                styles["Normal"],
            )
        )

    _CURRENT_REPORT = report
    try:
        doc.build(story)
    finally:
        _CURRENT_REPORT = None

    return output.getvalue(), report_service._filename(report, "pdf")
