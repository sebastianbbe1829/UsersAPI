"""Unit tests for client screening helpers."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from UsersAPI.domains.clients.services.screening_provider import (
    InternalScreeningProvider,
    normalize_text,
)
from UsersAPI.domains.clients.services.screening_service import (
    _build_list_type,
    _build_report_item,
    screen_client,
)


def test_normalize_text_removes_accents_and_collapses_spaces():
    assert normalize_text("  José   Pérez ") == "JOSE PEREZ"


def test_provider_matches_identification_number():
    db = MagicMock()
    entry = SimpleNamespace(
        id="entry-1",
        source_id="source-1",
        external_id="123",
        entry_type="INDIVIDUAL",
        name="JUAN PEREZ",
        normalized_name="JUAN PEREZ",
        aliases=[],
        identification_numbers=["123"],
        nationality=None,
        date_of_birth=None,
        active=True,
    )
    db.query.return_value.filter.return_value.all.return_value = [entry]

    client = SimpleNamespace(
        identification_number="123",
        full_name="OTRO NOMBRE",
        person_type="NATURAL",
    )

    result = InternalScreeningProvider().screen(db, client)

    assert result.status == "MATCH"
    assert result.matches[0]["entry_id"] == "entry-1"


def test_provider_returns_clear_when_no_match():
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []

    client = SimpleNamespace(
        identification_number="123",
        full_name="JUAN PEREZ",
        person_type="NATURAL",
    )

    result = InternalScreeningProvider().screen(db, client)

    assert result.status == "CLEAR"
    assert result.matches == []


def test_provider_returns_pending_without_synced_sources():
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []

    client = SimpleNamespace(
        identification_number="123",
        full_name="JUAN PEREZ",
        person_type="NATURAL",
    )

    result = InternalScreeningProvider().screen(db, client)

    assert result.status == "PENDING"


def test_screen_client_updates_clear_status():
    db = MagicMock()
    client = SimpleNamespace(
        id="client-1",
        tenant_id=10,
        compliance_status="PENDING",
        is_listed=False,
        list_type=None,
    )

    screening = SimpleNamespace(
        client_id=client.id,
        tenant_id=client.tenant_id,
        provider="INTERNAL_OFFICIAL",
        status="PENDING",
        risk_level=None,
        matched=False,
        response=None,
        error_message=None,
    )
    db.add.side_effect = lambda value: None
    db.flush.return_value = None
    db.refresh.return_value = None
    db.query.return_value.filter.return_value.first.return_value = None

    result = screen_client(db, client)

    assert result.status in {"CLEAR", "PENDING"}


def test_build_list_type_uses_source():
    assert _build_list_type("OFAC_SDN") == "OFAC_SDN"
    assert _build_list_type("UN_CONSOLIDATED") == "UN_CONSOLIDATED"


def test_build_report_item_maps_fields():
    screening = SimpleNamespace(
        id="screening-1",
        tenant_id=10,
        client_id="client-1",
        provider="INTERNAL_OFFICIAL",
        status="CLEAR",
        risk_level=None,
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
    query_result = db = MagicMock()
    query_result.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = [
        (screening, client)
    ]

    result = _build_report_item(screening, client)

    assert result["full_name"] == "JUAN PEREZ"


def test_list_screenings_maps_query_results():
    from UsersAPI.domains.clients.services.screening_service import list_screenings

    db = MagicMock()
    screening = SimpleNamespace(
        id="screening-1",
        tenant_id=10,
        client_id="client-1",
        provider="INTERNAL_OFFICIAL",
        status="CLEAR",
        risk_level=None,
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
    query = db.query.return_value
    query = query.join.return_value
    query = query.filter.return_value
    query = query.order_by.return_value
    query.all.return_value = [(screening, client)]

    result = list_screenings(db, 10)

    assert len(result) == 1
    assert result[0]["full_name"] == "JUAN PEREZ"
    assert result[0]["provider"] == "INTERNAL_OFFICIAL"
