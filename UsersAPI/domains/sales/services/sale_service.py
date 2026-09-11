from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from UsersAPI.domains.cash.services.cash_context_service import require_operational_context
from UsersAPI.domains.cash.services.cash_movement_service import record_automatic_movement
from UsersAPI.domains.clients.models import ClientDB
from UsersAPI.domains.clients.services.compliance_override_service import (
    has_compliance_override,
)
from UsersAPI.domains.inventory.models import InventoryDB, ProductDB
from UsersAPI.domains.inventory.schemas import InventoryMovementCreate
from UsersAPI.domains.inventory.services.inventory_movement_service import (
    create_inventory_movement,
)
from UsersAPI.domains.portfolio.models import CreditLimitDB, ObligationDB

from ..models import SaleCustomerDB, SaleDB, SaleItemDB, SalePaymentDB
from ..repositories import SaleRepository
from ..schemas import SaleCreate

MONEY_UNIT = Decimal("1")
CREDIT_METHODS = {"CREDITO"}


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_UNIT, rounding=ROUND_HALF_UP)


def _actor_name(current_user: object | None) -> str:
    return (
        getattr(current_user, "email", None) or getattr(current_user, "username", None) or "system"
    )


def _sale_price(inventory: InventoryDB, at_cost: bool = False) -> Decimal:
    if inventory.quantity <= 0 or inventory.purchase_price is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product has no available inventory price",
        )
    if at_cost:
        return _money(Decimal(inventory.purchase_price))
    return _money(
        Decimal(inventory.purchase_price)
        * (Decimal("1") + Decimal(inventory.profit_percentage or 0))
    )


def _client_is_eligible_for_sale(
    client: ClientDB,
    db: Session,
    tenant_id: int,
) -> bool:
    if client.status != "ACTIVE":
        return False
    if client.is_listed or client.compliance_status == "MATCH":
        return has_compliance_override(client.id, db, tenant_id)
    return True


def _credit_available(
    client_id: UUID,
    db: Session,
    tenant_id: int,
) -> Decimal:
    credit_limit = db.scalar(
        select(CreditLimitDB)
        .where(
            CreditLimitDB.tenant_id == tenant_id,
            CreditLimitDB.client_id == client_id,
            CreditLimitDB.active.is_(True),
        )
        .with_for_update()
    )
    if credit_limit is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Client does not have an active credit limit",
        )
    used = db.scalar(
        select(func.coalesce(func.sum(ObligationDB.balance), 0)).where(
            ObligationDB.tenant_id == tenant_id,
            ObligationDB.client_id == client_id,
            ObligationDB.status == "ACTIVE",
        )
    )
    return _money(
        max(
            Decimal("0"),
            Decimal(credit_limit.approved_limit) - Decimal(used or 0),
        )
    )


def create_sale(
    data: SaleCreate,
    db: Session,
    tenant_id: int,
    current_user: object,
    is_autoconsumption: bool = False,
) -> SaleDB:
    cash_context = require_operational_context(db, tenant_id, current_user)
    business_date = cash_context["business_date"]
    cash_register_id = cash_context.get("register_id")

    product_ids = [item.product_id for item in data.items]
    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A product cannot appear more than once in a sale",
        )

    if is_autoconsumption and Decimal(data.discount_percentage) != Decimal("0"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Autoconsumption sales cannot apply additional discounts",
        )

    payment_total = _money(
        sum(
            (Decimal(payment.amount) for payment in data.payments),
            Decimal("0"),
        )
    )
    normalized_methods = [payment.payment_method.strip().upper() for payment in data.payments]
    credit_amount = _money(
        sum(
            (
                Decimal(payment.amount)
                for payment, method in zip(data.payments, normalized_methods)
                if method in CREDIT_METHODS
            ),
            Decimal("0"),
        )
    )
    has_credit = credit_amount > 0

    if has_credit and len(data.customers) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credit sales cannot be split among multiple clients",
        )

    if has_credit and (
        len(data.customers) != 1
        or data.customers[0].client_id is None
        or data.customers[0].is_generic
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credit sales require exactly one registered client",
        )

    actor = _actor_name(current_user)
    repository = SaleRepository(db)
    sale = SaleDB(
        tenant_id=tenant_id,
        cash_register_id=cash_register_id,
        sale_number=repository.next_sale_number(tenant_id),
        business_date=business_date,
        status="PENDING" if has_credit else "COMPLETED",
        is_autoconsumption=is_autoconsumption,
        subtotal=Decimal("0"),
        discount_percentage=data.discount_percentage,
        discount_amount=Decimal("0"),
        total=Decimal("0"),
        created_by=actor,
    )
    repository.add(sale)
    db.flush()

    subtotal = Decimal("0")
    inventory_costs: dict[int, Decimal] = {}
    inventory_profits: dict[int, Decimal] = {}
    for item in data.items:
        inventory = db.scalar(
            select(InventoryDB)
            .where(
                InventoryDB.tenant_id == tenant_id,
                InventoryDB.product_id == item.product_id,
            )
            .with_for_update()
        )
        product = db.scalar(
            select(ProductDB).where(
                ProductDB.tenant_id == tenant_id,
                ProductDB.id == item.product_id,
            )
        )
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )
        if not product.active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inactive products cannot be sold",
            )
        if inventory is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Insufficient inventory for this sale",
            )

        inventory_costs[item.product_id] = Decimal(inventory.purchase_price or 0)
        inventory_profits[item.product_id] = Decimal(inventory.profit_percentage or 0)
        unit_price = _sale_price(inventory, at_cost=is_autoconsumption)
        line_total = _money(Decimal(item.quantity) * unit_price)
        subtotal += line_total
        sale.items.append(
            SaleItemDB(
                tenant_id=tenant_id,
                product_id=product.id,
                product_code=product.code,
                product_name=product.name,
                quantity=item.quantity,
                unit_price=unit_price,
                line_total=line_total,
            )
        )

    subtotal = _money(subtotal)
    discount_amount = _money(subtotal * Decimal(data.discount_percentage) / Decimal("100"))
    total = _money(subtotal - discount_amount)
    if payment_total != total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment total must equal sale total: {total}",
        )

    sale.subtotal = subtotal
    sale.discount_amount = discount_amount
    sale.total = total

    if not data.customers:
        if has_credit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credit sales require exactly one registered client",
            )
        sale.customers.append(
            SaleCustomerDB(
                tenant_id=tenant_id,
                customer_name="Consumidor final",
                allocation_percentage=Decimal("100"),
                allocation_amount=total,
                is_generic=True,
            )
        )
    else:
        percentage_total = sum(
            (Decimal(customer.allocation_percentage) for customer in data.customers),
            Decimal("0"),
        )
        if percentage_total != Decimal("100"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer allocation must total 100%",
            )

        allocation_total = Decimal("0")
        for index, customer in enumerate(data.customers):
            if customer.is_generic and customer.client_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Generic customer cannot have client_id",
                )
            if customer.client_id is None and not customer.is_generic:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Each customer must have client_id or be generic",
                )
            if has_credit and (customer.is_generic or customer.client_id is None):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Credit sales require a registered client",
                )

            customer_name = "Consumidor final"
            if customer.client_id is not None:
                query = select(ClientDB).where(
                    ClientDB.tenant_id == tenant_id,
                    ClientDB.id == customer.client_id,
                )
                if has_credit:
                    query = query.with_for_update()
                client = db.scalar(query)
                if client is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Client not found",
                    )
                if not _client_is_eligible_for_sale(client, db, tenant_id):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Client is not eligible for sales",
                    )
                if has_credit:
                    available = _credit_available(client.id, db, tenant_id)
                    if credit_amount > available:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"Insufficient available credit. Available credit: {available}"
                            ),
                        )
                customer_name = client.full_name

            if index == len(data.customers) - 1:
                allocation_amount = _money(total - allocation_total)
            else:
                allocation_amount = _money(
                    total * Decimal(customer.allocation_percentage) / Decimal("100")
                )
            allocation_total += allocation_amount
            sale.customers.append(
                SaleCustomerDB(
                    tenant_id=tenant_id,
                    client_id=customer.client_id,
                    customer_name=customer_name,
                    allocation_percentage=customer.allocation_percentage,
                    allocation_amount=allocation_amount,
                    is_generic=1 if customer.is_generic else 0,
                )
            )

    for payment, method in zip(data.payments, normalized_methods):
        sale.payments.append(
            SalePaymentDB(
                tenant_id=tenant_id,
                cash_register_id=cash_register_id,
                payment_method=method,
                amount=_money(Decimal(payment.amount)),
            )
        )

    if has_credit:
        obligation = ObligationDB(
            tenant_id=tenant_id,
            cash_register_id=cash_register_id,
            client_id=data.customers[0].client_id,
            sale_id=sale.id,
            business_date=business_date,
            initial_amount=credit_amount,
            balance=credit_amount,
            status="ACTIVE",
            created_by=actor,
        )
        db.add(obligation)

    db.flush()
    for item in sale.items:
        create_inventory_movement(
            InventoryMovementCreate(
                product_id=item.product_id,
                movement_type="EXIT",
                origin_type="SALE",
                origin_id=sale.id,
                quantity=item.quantity,
                unit_purchase_price=inventory_costs[item.product_id],
                profit_percentage=0 if is_autoconsumption else inventory_profits[item.product_id],
                notes=(
                    f"Venta {sale.sale_number} - Autoconsumo"
                    if is_autoconsumption
                    else f"Venta {sale.sale_number}"
                ),
            ),
            db,
            tenant_id,
            current_user,
        )

    for payment, method in zip(data.payments, normalized_methods):
        if method in CREDIT_METHODS or Decimal(payment.amount) == 0:
            continue
        record_automatic_movement(
            db=db,
            tenant_id=tenant_id,
            amount=_money(Decimal(payment.amount)),
            payment_method=method,
            origin_type="SALE",
            origin_id=sale.id,
            description=f"Venta {sale.sale_number}",
            current_user=current_user,
        )

    db.flush()
    return repository.get_by_id(tenant_id, sale.id) or sale


def get_sale(sale_id: UUID, db: Session, tenant_id: int) -> SaleDB:
    sale = SaleRepository(db).get_by_id(tenant_id, sale_id)
    if sale is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sale not found",
        )
    return sale


def list_sales(
    db: Session,
    tenant_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[SaleDB]:
    return SaleRepository(db).list(tenant_id, limit=limit, offset=offset)
