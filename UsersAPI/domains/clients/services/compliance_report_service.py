from sqlalchemy import desc, exists
from sqlalchemy.orm import Session

from ..models import ClientComplianceOverrideDB, ClientDB, ClientScreeningDB


def list_restricted_clients_report(db: Session, tenant_id: int):
    historical_match = exists().where(
        ClientScreeningDB.client_id == ClientDB.id,
        ClientScreeningDB.tenant_id == tenant_id,
        ClientScreeningDB.status == "MATCH",
    )
    clients = (
        db.query(ClientDB)
        .filter(
            ClientDB.tenant_id == tenant_id,
            ClientDB.is_listed.is_(True) | historical_match,
        )
        .order_by(desc(ClientDB.created_at))
        .all()
    )
    result = []
    for client in clients:
        screening = (
            db.query(ClientScreeningDB)
            .filter(
                ClientScreeningDB.tenant_id == tenant_id,
                ClientScreeningDB.client_id == client.id,
            )
            .order_by(desc(ClientScreeningDB.requested_at))
            .first()
        )
        latest_override = (
            db.query(ClientComplianceOverrideDB)
            .filter(
                ClientComplianceOverrideDB.tenant_id == tenant_id,
                ClientComplianceOverrideDB.client_id == client.id,
            )
            .order_by(desc(ClientComplianceOverrideDB.created_at))
            .first()
        )

        lifted = bool(
            latest_override
            and screening
            and latest_override.created_at >= screening.requested_at
            and screening.status == "MATCH"
            and client.status == "ACTIVE"
        )
        report_status = (
            "LEVANTADA" if lifted else "BLOQUEADO" if client.status == "BLOCKED" else client.status
        )

        result.append(
            {
                "client_id": client.id,
                "identification_number": client.identification_number,
                "full_name": client.full_name,
                "person_type": client.person_type,
                "status": client.status,
                "report_status": report_status,
                "compliance_status": client.compliance_status,
                "list_type": client.list_type,
                "is_listed": client.is_listed,
                "client_created_at": client.created_at,
                "client_created_by": client.created_by,
                "screening_id": screening.id if screening else None,
                "screening_requested_at": (screening.requested_at if screening else None),
                "screening_completed_at": (screening.completed_at if screening else None),
                "screening_status": screening.status if screening else None,
                "screening_risk_level": (screening.risk_level if screening else None),
                "screening_matched": screening.matched if screening else None,
                "screening_error": (screening.error_message if screening else None),
            }
        )
    return result


def list_compliance_override_history(db: Session, tenant_id: int):
    rows = (
        db.query(ClientComplianceOverrideDB, ClientDB)
        .join(ClientDB, ClientDB.id == ClientComplianceOverrideDB.client_id)
        .filter(ClientComplianceOverrideDB.tenant_id == tenant_id)
        .order_by(desc(ClientComplianceOverrideDB.created_at))
        .all()
    )
    return [
        {
            "id": override.id,
            "client_id": override.client_id,
            "identification_number": client.identification_number,
            "full_name": client.full_name,
            "screening_id": override.screening_id,
            "requested_by": override.requested_by,
            "requested_by_email": override.requested_by_email,
            "reason": override.reason,
            "created_at": override.created_at,
        }
        for override, client in rows
    ]
