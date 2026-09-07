from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from UsersAPI.domains.clients.services.screening_provider import (
    ScreeningProvider,
    normalize_screening_text,
)
from UsersAPI.domains.clients.services.screening_report_service import list_screenings
from UsersAPI.domains.clients.services.screening_service import screen_client


def test_normalize_screening_text_removes_accents_and_symbols():
    assert normalize_screening_text("José Pérez #123") == "JOSE PEREZ 123"


def test_screening_provider_returns_pending_without_sources():
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []
    client = SimpleNamespace(full_name="JUAN PEREZ", identification_number="123")

    result = ScreeningProvider().screen(client, db)

    assert result.status == "PENDING"
    assert result.risk_level == "UNKNOWN"
    assert result.matched is False


def test_screening_provider_returns_match_on_document():
    source = SimpleNamespace(id=uuid4(), code="OFAC_SDN", name="OFAC")
    entry = SimpleNamespace(
        source=source,
        source_id=source.id,
        active=True,
        normalized_name="OTHER NAME",
        identification_numbers=["123"],
        aliases=[],
        external_id="12345",
        name="OTHER NAME",
        entry_type="INDIVIDUAL",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.all.side_effect = [[source], [entry]]
    client = SimpleNamespace(full_name="JUAN PEREZ", identification_number="123")

    result = ScreeningProvider().screen(client, db)

    assert result.status == "MATCH"
    assert result.risk_level == "HIGH"
    assert result.matched is True
    assert result.list_type == "OFAC_SDN"


def test_screen_client_updates_client_on_clear():
    db = MagicMock()
    client = SimpleNamespace(id=uuid4(), tenant_id=10, compliance_status="PENDING", is_listed=False, list_type=None)
    provider_result = SimpleNamespace(
        status="CLEAR",
        risk_level="LOW",
        matched=False,
        list_type=None,
        response={"matches": []},
    )

    with patch(
        "UsersAPI.domains.clients.services.screening_service.ScreeningProvider.screen",
        return_value=provider_result,
    ):
        result = screen_client(client, db)

    assert result.status == "CLEAR"
    assert result.matched is False
    assert client.compliance_status == "CLEAR"
    assert client.is_listed is False


def test_screen_client_records_error_without_raising():
    db = MagicMock()
    client = SimpleNamespace(id=uuid4(), tenant_id=10, compliance_status="PENDING", is_listed=False, list_type=None)

    with patch(
        "UsersAPI.domains.clients.services.screening_service.ScreeningProvider.screen",
        side_effect=RuntimeError("source unavailable"),
    ):
        result = screen_client(client, db)

    assert result.status == "ERROR"
    assert "source unavailable" in result.error_message
    assert client.compliance_status == "ERROR"


def test_list_screenings_isolated_by_tenant():
    db = MagicMock()
    screening = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        provider="INTERNAL_OFFICIAL",
        status="CLEAR",
        risk_level="LOW",
        matched=False,
        requested_at=None,
        completed_at=None,
        response={"matches": []},
        error_message=None,
    )
    client = SimpleNamespace(
        id=screening.client_id,
        identification_number="123",
        full_name="JUAN PEREZ",
        person_type="NATURAL",
        tenant_id=10,
        list_type=None,
    )
    db.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = [
        (screening, client)
    ]

    result = list_screenings(db, 10)

    assert len(result) == 1
    assert result[0]["full_name"] == "JUAN PEREZ"
    assert result[0]["provider"] == "INTERNAL_OFFICIAL"
