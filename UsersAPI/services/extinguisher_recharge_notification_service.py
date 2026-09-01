from datetime import date

from sqlalchemy import and_, select
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
from ..settings import settings


ADMIN_ROLE_CODES = ("ADMIN",)


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
                try:
                    send_email(
                        recipient=recipient,
                        subject=subject,
                        message=message,
                        tenant_slug=data["tenant_slug"],
                        tenant_name=data["tenant_name"],
                        template="default",
                    )
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
        application_name = (
            settings.email_from_name.strip()
            if settings.email_from_name and settings.email_from_name.strip()
            else "Gestión de Extintores"
        )

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
