"""Unit tests for client screening helpers."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from UsersAPI.domains.clients.services.screening_provider import (
    ScreeningProvider,
    normalize_screening_text,
)
from UsersAPI.domains.clients.services.screening_service import (
    _build_report_item,
    screen_client,
)


def _query_results(source_results, entry_results):
    db = MagicMock()
    source_query = db.query.return_value
    source_query.filter.return_value.all.return_value = source_results
    entry_query = MagicMock()
    entry_query.filter.return_value.all.return_value = entry_results
    db.query.side_effect = [source_query, entry_query]
    return db


def test_normalize_text_removes_accents_and_collapses_spaces():
    assert normalize_screening_text("  José   Pérez ") == "JOSE PEREZ"


def test_provider_matches_identification_number():
    source = SimpleNamespace(id="source-1", code="OFAC_SDN", name="OFAC SDN")
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
        source=source,
    )
    db = _query_results([source], [entry])
    client = SimpleNamespace(
        identification_number="123",
        full_name="OTRO NOMBRE",
        person_type="NATURAL",
    )

    result = ScreeningProvider().screen(client, db)

    assert result.status == "MATCH"
    assert result.matched is True
    assert result.response["matches"][0]["external_id"] == "123"


def test_provider_returns_clear_when_no_match():
    source = SimpleNamespace(id="source-1", code="OFAC_SDN", name="OFAC SDN")
    db = _query_results([source], [])
    client = SimpleNamespace(
        identification_number="123",
        full_name="JUAN PEREZ",
        person_type="NATURAL",
    )

    result = ScreeningProvider().screen(client, db)

    assert result.status == "CLEAR"
    assert result.response["matches"] == []


def test_provider_returns_pending_without_synced_sources():
    db = _query_results([], [])
    client = SimpleNamespace(
        identification_number="123",
        full_name="JUAN PEREZ",
        person_type="NATURAL",
    )

    result = ScreeningProvider().screen(client, db)

    assert result.status == "PENDING"


def test_screen_client_updates_clear_status():
    source = SimpleNamespace(id="source-1", code="OFAC_SDN", name="OFAC SDN")
    db = _query_results([source], [])
    db.flush.return_value = None
    client = SimpleNamespace(
        id="client-1",
        tenant_id=10,
        identification_number="123",
        full_name="JUAN PEREZ",
        compliance_status="PENDING",
        is_listed=False,
        list_type=None,
    )

    result = screen_client(client, db)

    assert result.status == "CLEAR"
    assert client.compliance_status == "CLEAR"
    assert client.is_listed is False


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
