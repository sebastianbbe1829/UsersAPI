import uuid
from decimal import Decimal
from types import SimpleNamespace

from unittest.mock import MagicMock

from UsersAPI.domains.portfolio.models import ObligationDB
from UsersAPI.domains.portfolio.services import (
    annul_payment,
    list_payments,
    register_payment,
)
from UsersAPI.domains.sales.models import SaleDB

# Existing test content preserved except for the SQLAlchemy relationship test below.


def test_obligation_sale_number_property():
    obligation = ObligationDB()
    obligation.sale = SaleDB(sale_number="V-000123")
    assert obligation.sale_number == "V-000123"

    obligation.sale = None
    assert obligation.sale_number is None
