from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ..models import ClientDB, ClientScreeningDB
from .screening_provider import ScreeningProvider


def screen_client(client: ClientDB, db: Session) -> ClientScreeningDB:
    screening = ClientScreeningDB(
        tenant_id=client.tenant_id,
        client_id=client.id,
        provider=ScreeningProvider.code,
        status="PENDING",
        requested_at=datetime.now(UTC),
    )
    db.add(screening)
    db.flush()

    try:
        result = ScreeningProvider().screen(client, db)
        completed_at = datetime.now(UTC)
        screening.status = result.status
        screening.risk_level = result.risk_level
        screening.matched = result.matched
        screening.response = result.response
        screening.completed_at = completed_at
        screening.error_message = None

        client.compliance_status = result.status
        client.is_listed = result.matched
        client.list_type = result.list_type

        if result.matched or result.status == "MATCH":
            client.status = "BLOCKED"
        elif result.status == "CLEAR":
            # A fresh screening with no match removes the current compliance
            # restriction. A persistent MATCH remains BLOCKED and requires
            # the explicit override flow.
            client.status = "ACTIVE"
        elif result.status in {"PENDING", "ERROR"} and client.status != "BLOCKED":
            client.status = "INACTIVE"
    except Exception as exc:
        screening.status = "ERROR"
        screening.risk_level = "UNKNOWN"
        screening.matched = False
        screening.completed_at = datetime.now(UTC)
        screening.error_message = str(exc)[:2000]
        client.compliance_status = "ERROR"
        client.is_listed = False
        client.list_type = None
        if client.status != "BLOCKED":
            client.status = "INACTIVE"

    db.add(screening)
    db.add(client)
    db.flush()
    return screening
