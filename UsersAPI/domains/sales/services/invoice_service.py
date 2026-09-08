import base64
import html
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from UsersAPI.domains.clients.models import ClientDB
from UsersAPI.util.email_utils import send_email

from ..models import SaleDB
from .sale_service import get_sale


def _money(value: Decimal) -> str:
    return f"${Decimal(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _invoice_html(sale: SaleDB) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(item.product_code)}</td><td>{html.escape(item.product_name)}</td>"
        f"<td>{item.quantity}</td><td>{_money(item.unit_price)}</td><td>{_money(item.line_total)}</td></tr>"
        for item in sale.items
    )
    customers = "".join(
        f"<li>{html.escape(customer.customer_name)} - {customer.allocation_percentage}% "
        f"({_money(customer.allocation_amount)})</li>"
        for customer in sale.customers
    )
    payments = "".join(
        f"<li>{html.escape(payment.payment_method)} - {_money(payment.amount)}</li>"
        for payment in sale.payments
    )
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>Factura {html.escape(sale.sale_number)}</title>
<style>body{{font-family:Arial,sans-serif;margin:32px;color:#222}}h1{{margin-bottom:4px}}table{{width:100%;border-collapse:collapse;margin-top:24px}}th,td{{border:1px solid #ddd;padding:8px;text-align:left}}th{{background:#f5f5f5}}.total{{font-size:20px;font-weight:bold;text-align:right;margin-top:20px}}.columns{{display:flex;gap:48px}}.columns>div{{flex:1}}</style>
</head><body><h1>Factura {html.escape(sale.sale_number)}</h1>
<p>Estado: {html.escape(sale.status)}</p>
<table><thead><tr><th>Código</th><th>Producto</th><th>Cantidad</th><th>Precio</th><th>Total</th></tr></thead><tbody>{rows}</tbody></table>
<p>Subtotal: {_money(sale.subtotal)}<br>Descuento ({sale.discount_percentage}%): {_money(sale.discount_amount)}</p>
<div class="total">Total: {_money(sale.total)}</div>
<div class="columns"><div><h3>Cliente(s)</h3><ul>{customers}</ul></div><div><h3>Pagos</h3><ul>{payments}</ul></div></div>
</body></html>"""


def send_invoice_email(sale_id, db: Session, tenant_id: int) -> list[str]:
    sale = get_sale(sale_id, db, tenant_id)
    recipient_ids = {customer.client_id for customer in sale.customers if customer.client_id is not None}
    if not recipient_ids:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The sale has no registered customers with email")

    clients = db.scalars(select(ClientDB).where(ClientDB.tenant_id == tenant_id, ClientDB.id.in_(recipient_ids))).all()
    recipients = sorted({str(client.email) for client in clients if client.email})
    if not recipients:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The sale customers do not have an email configured")

    invoice_html = _invoice_html(sale)
    attachment = {
        "name": f"factura-{sale.sale_number}.html",
        "content": base64.b64encode(invoice_html.encode("utf-8")).decode("ascii"),
    }
    try:
        for recipient in recipients:
            send_email(
                recipient=recipient,
                subject=f"Factura {sale.sale_number}",
                message=f"Adjuntamos la factura {sale.sale_number} por un total de {_money(sale.total)}.",
                template="default",
                attachments=[attachment],
            )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="The invoice email could not be sent") from exc
    return recipients
