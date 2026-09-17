"""Compatibilidad para consumidores existentes del contexto operativo."""

from ....application.operational_context import (
    get_user_operational_context,
    validate_operational_context,
)


def get_user_cash_context(db, tenant_id: int, user_tenant_id: int) -> dict:
    return get_user_operational_context(db, tenant_id, user_tenant_id)


def require_operational_context(db, tenant_id: int, current_user) -> dict:
    return validate_operational_context(
        get_user_cash_context(
            db,
            tenant_id,
            int(getattr(current_user, "id", 0)),
        )
    )

__all__ = [
    "get_user_cash_context",
    "require_operational_context",
]
