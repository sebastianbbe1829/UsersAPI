from datetime import date

from sqlalchemy import and_, select, text
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
NOTIFICATION_LOG_TABLE = "users_api.extinguisher_recharge_notification_log"


class ExtinguisherRechargeNotificationService:
    """Envía el aviso diario de extintores cuya recarga vence hoy."""

    def __init__(self, db: Session):
        self.db = db
        self._ensure_notification_log_table()

    def _ensure_notification_log_table(self) -> None:
        """Crea el registro de idempotencia si aún no existe.

        El job puede ejecutarse más de una vez durante la ventana de respaldo.
        Este registro garantiza que un mismo tenant/administrador/fecha reciba
        como máximo una notificación exitosa.
        """
        self.db.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {NOTIFICATION_LOG_TABLE} (
                    notification_date DATE NOT NULL,
                    tenant_id BIGINT NOT NULL,
                    recipient VARCHAR(320) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    sent_at TIMESTAMPTZ NULL,
                    PRIMARY KEY (notification_date, tenant_id, recipient)
                )
                """
            )
        )
        self.db.commit()

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
        status = self.db.execute(
            text(
                f"""
                SELECT status
                FROM {NOTIFICATION_LOG_TABLE}
                WHERE notification_date = :notification_date
                  AND tenant_id = :tenant_id
                  AND recipient = :recipient
                """
            ),
            {
                "notification_date": target_date,
                "tenant_id": tenant_id,
                "recipient": recipient,
            },
        ).scalar_one_or_none()
        return status == "sent"

    def _mark_pending(self, target_date: date, tenant_id: int, recipient: str) -> None:
        self.db.execute(
            text(
                f"""
                INSERT INTO {NOTIFICATION_LOG_TABLE}
                    (notification_date, tenant_id, recipient, status)
                VALUES
                    (:notification_date, :tenant_id, :recipient, 'pending')
                ON CONFLICT (notification_date, tenant_id, recipient)
                DO UPDATE SET status = 'pending'
                WHERE {NOTIFICATION_LOG_TABLE}.status <> 'sent'
                """
            ),
            {
                "notification_date": target_date,
                "tenant_id": tenant_id,
                "recipient": recipient,
            },
        )
        self.db.commit()

    def _mark_sent(self, target_date: date, tenant_id: int, recipient: str) -> None:
        self.db.execute(
            text(
                f"""
                UPDATE {NOTIFICATION_LOG_TABLE}
                SET status = 'sent', sent_at = NOW()
                WHERE notification_date = :notification_date
                  AND tenant_id = :tenant_id
                  AND recipient = :recipient
                """
            ),
            {
                "notification_date": target_date,
                "tenant_id": tenant_id,
                "recipient": recipient,
            },
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
        # El nombre que identifica la aplicación en este correo debe ser
        # siempre el del tenant que recibe la notificación. No usamos un
        # nombre global/fijo de aplicación (por ejemplo, "Info Fenix").
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
