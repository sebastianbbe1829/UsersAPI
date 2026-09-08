from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from UsersAPI.domains.inventory.services import inventory_movement_service as movement_service


def test_list_movements_rejects_invalid_date_range():
    with pytest.raises(HTTPException) as error:
        movement_service.list_inventory_movements(
            MagicMock(),
            7,
            from_date=date(2026, 9, 8),
            to_date=date(2026, 9, 7),
        )

    assert error.value.status_code == 400


def test_get_movement_not_found(monkeypatch):
    repository = MagicMock()
    repository.get_by_id.return_value = None
    monkeypatch.setattr(
        movement_service,
        "InventoryMovementRepository",
        lambda _db: repository,
    )

    with pytest.raises(HTTPException) as error:
        movement_service.get_inventory_movement(MagicMock(), 7, uuid4())

    assert error.value.status_code == 404
