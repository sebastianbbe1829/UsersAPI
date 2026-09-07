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

        # A compliance MATCH is a hard business restriction. It can only be
        # lifted through the explicit compliance-override flow.
        if result.matched or result.status == "MATCH":
            client.status = "BLOCKED"
    except Exception as exc:
        screening.status = "ERROR"
        screening.risk_level = "UNKNOWN"
        screening.matched = False
        screening.completed_at = datetime.now(UTC)
        screening.error_message = str(exc)[:2000]
        client.compliance_status = "ERROR"
        client.is_listed = False
        client.list_type = None

    db.add(screening)
    db.add(client)
    db.flush()
    return screening
