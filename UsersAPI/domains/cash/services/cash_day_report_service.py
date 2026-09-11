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
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
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
PORTFOLIO_PAYMENT_METHODS = [
    "Efectivo",
    "Transferencias",
    "PSE",
    "Tarjeta",
    "Crédito",
]
COLOMBIA_TZ = ZoneInfo("America/Bogota")


# The remainder of this file is unchanged except for the PDF layout helper and
# the two adjacent payment-method sections below.
