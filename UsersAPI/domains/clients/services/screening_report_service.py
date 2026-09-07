from uuid import UUID

from sqlalchemy.orm import Session

from ..models import ClientDB, ClientScreeningDB


def list_screenings(
    db: Session,
    tenant_id: int,
    client_id: UUID | None = None,
) -> list[dict]:
    query = (
        db.query(ClientScreeningDB, ClientDB)
        .join(ClientDB, ClientDB.id == ClientScreeningDB.client_id)
        .filter(
            ClientScreeningDB.tenant_id == tenant_id,
            ClientDB.tenant_id == tenant_id,
        )
        .order_by(ClientScreeningDB.requested_at.desc())
    )
    if client_id is not None:
        query = query.filter(ClientScreeningDB.client_id == client_id)

    return [
        {
            "id": screening.id,
            "client_id": client.id,
            "identification_number": client.identification_number,
            "full_name": client.full_name,
            "person_type": client.person_type,
            "provider": screening.provider,
            "status": screening.status,
            "risk_level": screening.risk_level,
            "matched": screening.matched,
            "list_type": client.list_type,
            "requested_at": screening.requested_at,
            "completed_at": screening.completed_at,
            "response": screening.response,
            "error_message": screening.error_message,
        }
        for screening, client in query.all()
    ]
