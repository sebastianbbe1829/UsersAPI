import base64
from decimal import Decimal
from io import BytesIO

from fastapi import HTTPException, status
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from UsersAPI.domains.clients.models import ClientDB
from UsersAPI.domains.core.repositories.tenant_repository import TenantRepository
from UsersAPI.util.email_utils import send_email

from ..models import SaleDB
from .sale_service import get_sale


def _money(value: Decimal) -> str:
    return f"${Decimal(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _invoice_pdf(sale: SaleDB) -> bytes:
    """Generate the printable invoice as a PDF in memory."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"Factura {sale.sale_number}",
        author="Sistema de Ventas",
    )
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    small_style = styles["Normal"]
    right_style = styles["Normal"].clone("invoice-right")
    right_style.alignment = TA_RIGHT

    story = [
        Paragraph(f"Factura {sale.sale_number}", title_style),
        Paragraph(f"Estado: {sale.status}", small_style),
        Paragraph(
            f"Fecha: {sale.created_at.strftime('%d/%m/%Y %H:%M') if sale.created_at else '—'}",
            small_style,
        ),
        Spacer(1, 8 * mm),
    ]

    rows = [["Código", "Producto", "Cantidad", "Precio", "Total"]]
    for item in sale.items:
        rows.append(
            [
                str(item.product_code),
                str(item.product_name),
                str(item.quantity),
                _money(item.unit_price),
                _money(item.line_total),
            ]
        )
    items_table = Table(
        rows,
        colWidths=[25 * mm, 75 * mm, 25 * mm, 30 * mm, 30 * mm],
        repeatRows=1,
    )
    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(items_table)
    story.append(Spacer(1, 6 * mm))

    summary = [
        ["Subtotal", _money(sale.subtotal)],
        [f"Descuento ({sale.discount_percentage}%)", _money(sale.discount_amount)],
        ["TOTAL", _money(sale.total)],
    ]
    summary_table = Table(
        summary,
        colWidths=[45 * mm, 40 * mm],
        hAlign="RIGHT",
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, -1), (-1, -1), 12),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 7 * mm))

    customers = (
        "<br/>".join(
            (
                f"{customer.customer_name} — {customer.allocation_percentage}% — "
                f"{_money(customer.allocation_amount)}"
            )
            for customer in sale.customers
        )
        or "Consumidor final"
    )
    payments = "<br/>".join(
        f"{payment.payment_method} — {_money(payment.amount)}" for payment in sale.payments
    )
    details = Table(
        [
            [
                Paragraph("<b>Cliente(s)</b>", small_style),
                Paragraph("<b>Pagos</b>", small_style),
            ],
            [
                Paragraph(customers, small_style),
                Paragraph(payments, small_style),
            ],
        ],
        colWidths=[90 * mm, 90 * mm],
    )
    details.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#dddddd"),
                ),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f5f5")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(details)

    document.build(story)
    return buffer.getvalue()


def send_invoice_email(sale_id, db: Session, tenant_id: int) -> list[str]:
    sale = get_sale(sale_id, db, tenant_id)
    recipient_ids = {
        customer.client_id for customer in sale.customers if customer.client_id is not None
    }
    if not recipient_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The sale has no registered customers with email",
        )

    clients = db.scalars(
        select(ClientDB).where(
            ClientDB.tenant_id == tenant_id,
            ClientDB.id.in_(recipient_ids),
        )
    ).all()
    recipients = sorted({str(client.email) for client in clients if client.email})
    if not recipients:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The sale customers do not have an email configured",
        )

    attachment = {
        "name": f"factura-{sale.sale_number}.pdf",
        "content": base64.b64encode(_invoice_pdf(sale)).decode("ascii"),
    }

    tenant_repository = TenantRepository(db)
    tenant = tenant_repository.get_by_id(tenant_id=tenant_id)
    tenant_slug = tenant.slug
    tenant_name = tenant.name
    try:
        for recipient in recipients:
            send_email(
                recipient=recipient,
                subject=f"Factura {sale.sale_number}",
                message=(
                    f"Adjuntamos la factura {sale.sale_number} por un total de "
                    f"{_money(sale.total)}."
                ),
                template="default",
                tenant_slug=tenant_slug,
                tenant_name=tenant_name,
                attachments=[attachment],
            )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The invoice email could not be sent",
        ) from exc
    return recipients
