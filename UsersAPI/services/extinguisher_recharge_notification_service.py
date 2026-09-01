from datetime import date

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    and_,
    func,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ..models import (
    ExtinguisherDB,
    ExtinguisherTypeDB,
    RoleDB,
    TenantDB,
    UserTenantDB,
    UserTenantRoleDB,
)
from ..util.email_utils import send_email
from ..logging_config import logger


ADMIN_ROLE_CODES = ("ADMIN",)

# This table is created and versioned exclusively by Alembic. The service only
# describes its columns so SQLAlchemy Core can generate parameterized queries.
_NOTIFICATION_METADATA = MetaData()
NOTIFICATION_LOG_TABLE = Table(
    "extinguisher_recharge_notification_log",
    _NOTIFICATION_METADATA,
    Column("notification_date", Date, nullable=False),
    Column("tenant_id", Integer, nullable=False),
    Column("recipient", String(320), nullable=False),
    Column("status", String(20), nullable=False),
    Column("sent_at", DateTime(timezone=True), nullable=True),
    schema="users_api",
)


class ExtinguisherRechargeNotificationService:
    """Envía el aviso diario de extintores cuya recarga vence hoy."""

    def __init__(self, db: Session):
        self.db = db

    def run(self, notification_date: date | None = None) -> dict:
        target_date = notification_date or date.today()

        rows = self.db.execute(
            select(
                ExtinguisherDB,
                ExtinguisherTypeDB.name.label("type_name"),
                TenantDB.name.label("tenant_name"),
                TenantDB.slug.label("tenant_slug"),
            )
            .join(
                ExtinguisherTypeDB,
                ExtinguisherTypeDB.id == ExtinguisherDB.extinguisher_type_id,
            )
            .join(TenantDB, TenantDB.id == ExtinguisherDB.tenant_id)
            .where(
                and_(
                    ExtinguisherDB.active.is_(True),
                    ExtinguisherDB.next_recharge_date == target_date,
                    TenantDB.status == 1,
                )
            )
            .order_by(TenantDB.id, ExtinguisherDB.id)
        ).all()

        by_tenant: dict[int, dict] = {}
        for extinguisher, type_name, tenant_name, tenant_slug in rows:
            bucket = by_tenant.setdefault(
                extinguisher.tenant_id,
                {
                    "tenant_name": tenant_name,
                    "tenant_slug": tenant_slug,
                    "extinguishers": [],
                },
            )
            bucket["extinguishers"].append(
                {
                    "code": extinguisher.code,
                    "type_name": type_name,
                    "capacity": extinguisher.capacity,
                    "location": extinguisher.location,
                    "next_recharge_date": extinguisher.next_recharge_date,
                }
            )

        sent = 0
        skipped = 0
        errors = 0

        for tenant_id, data in by_tenant.items():
            recipients = self._get_admin_recipients(tenant_id)

            if not recipients:
                logger.warning(
                    "No active ADMIN email found for tenant_id=%s; recharge notification skipped",
                    tenant_id,
                )
                skipped += 1
                continue

            message = self._build_message(
                data["tenant_name"],
                target_date,
                data["extinguishers"],
            )
            subject = (
                f"Alerta: {len(data['extinguishers'])} extintor(es) "
                f"con recarga vencida hoy - {data['tenant_name']}"
            )

            for recipient in recipients:
                recipient_key = recipient.strip().lower()
                if self._already_sent(target_date, tenant_id, recipient_key):
                    logger.info(
                        "Recharge notification already sent for date=%s tenant_id=%s recipient=%s",
                        target_date,
                        tenant_id,
                        recipient,
                    )
                    continue

                self._mark_pending(target_date, tenant_id, recipient_key)
                try:
                    send_email(
                        recipient=recipient,
                        subject=subject,
                        message=message,
                        tenant_slug=data["tenant_slug"],
                        tenant_name=data["tenant_name"],
                        template="default",
                    )
                    self._mark_sent(target_date, tenant_id, recipient_key)
                    sent += 1
                except Exception:
                    self._clear_pending(target_date, tenant_id, recipient_key)
                    errors += 1
                    logger.exception(
                        "Error sending recharge notification to %s for tenant_id=%s",
                        recipient,
                        tenant_id,
                    )

        result = {
            "date": target_date.isoformat(),
            "tenants_with_expired_recharges": len(by_tenant),
            "extinguishers": len(rows),
            "emails_sent": sent,
            "tenants_without_admin_email": skipped,
            "email_errors": errors,
        }

        logger.info("Daily extinguisher recharge notification finished: %s", result)
        return result

    def _already_sent(self, target_date: date, tenant_id: int, recipient: str) -> bool:
        return (
            self.db.execute(
                select(NOTIFICATION_LOG_TABLE.c.status).where(
                    and_(
                        NOTIFICATION_LOG_TABLE.c.notification_date == target_date,
                        NOTIFICATION_LOG_TABLE.c.tenant_id == tenant_id,
                        NOTIFICATION_LOG_TABLE.c.recipient == recipient,
                    )
                )
            ).scalar_one_or_none()
            == "sent"
        )

    def _mark_pending(self, target_date: date, tenant_id: int, recipient: str) -> None:
        statement = (
            pg_insert(NOTIFICATION_LOG_TABLE)
            .values(
                notification_date=target_date,
                tenant_id=tenant_id,
                recipient=recipient,
                status="pending",
            )
            .on_conflict_do_update(
                index_elements=[
                    NOTIFICATION_LOG_TABLE.c.notification_date,
                    NOTIFICATION_LOG_TABLE.c.tenant_id,
                    NOTIFICATION_LOG_TABLE.c.recipient,
                ],
                set_={"status": "pending"},
                where=NOTIFICATION_LOG_TABLE.c.status != "sent",
            )
        )
        self.db.execute(statement)
        self.db.commit()

    def _clear_pending(self, target_date: date, tenant_id: int, recipient: str) -> None:
        self.db.execute(
            NOTIFICATION_LOG_TABLE.delete().where(
                and_(
                    NOTIFICATION_LOG_TABLE.c.notification_date == target_date,
                    NOTIFICATION_LOG_TABLE.c.tenant_id == tenant_id,
                    NOTIFICATION_LOG_TABLE.c.recipient == recipient,
                    NOTIFICATION_LOG_TABLE.c.status == "pending",
                )
            )
        )
        self.db.commit()

    def _mark_sent(self, target_date: date, tenant_id: int, recipient: str) -> None:
        self.db.execute(
            update(NOTIFICATION_LOG_TABLE)
            .where(
                and_(
                    NOTIFICATION_LOG_TABLE.c.notification_date == target_date,
                    NOTIFICATION_LOG_TABLE.c.tenant_id == tenant_id,
                    NOTIFICATION_LOG_TABLE.c.recipient == recipient,
                )
            )
            .values(status="sent", sent_at=func.now())
        )
        self.db.commit()

    def _get_admin_recipients(self, tenant_id: int) -> list[str]:
        rows = self.db.execute(
            select(UserTenantDB.email)
            .join(
                UserTenantRoleDB,
                UserTenantRoleDB.user_tenant_id == UserTenantDB.id,
            )
            .join(RoleDB, RoleDB.id == UserTenantRoleDB.role_id)
            .where(
                and_(
                    UserTenantDB.tenant_id == tenant_id,
                    UserTenantDB.status == 1,
                    RoleDB.tenant_id == tenant_id,
                    RoleDB.code.in_(ADMIN_ROLE_CODES),
                    RoleDB.status == 1,
                )
            )
            .distinct()
        ).scalars().all()

        return [email.strip() for email in rows if email and email.strip()]

    @staticmethod
    def _build_message(
        tenant_name: str,
        target_date: date,
        extinguishers: list[dict],
    ) -> str:
        application_name = (tenant_name or "Gestión de Extintores").strip()

        lines = [
            f"Buenos días, {tenant_name}.",
            "",
            "Los siguientes extintores tienen la fecha de recarga programada para hoy:",
            "",
        ]

        for item in extinguishers:
            details = [item["code"]]
            if item["type_name"]:
                details.append(item["type_name"])
            if item["capacity"]:
                details.append(str(item["capacity"]))

            line = f"- {' — '.join(details)}"
            if item["location"]:
                line += f" | Ubicación: {item['location']}"
            line += f" | Fecha: {item['next_recharge_date'].isoformat()}"
            lines.append(line)

        lines.extend(
            [
                "",
                "Por favor, realiza la gestión correspondiente de recarga y actualiza la información en el sistema.",
                "",
                f"Este es un mensaje automático generado por {application_name}.",
            ]
        )

        return "\n".join(lines)
