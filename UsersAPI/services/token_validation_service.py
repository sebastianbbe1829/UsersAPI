import math

from datetime import datetime, timezone

from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ..database import set_rls_tenant
from ..logging_config import logger
from ..models import UserTenantDB, TenantDB
from .jwt_service import ALGORITHM, SECRET_KEY


def validate_token(token: str, db: Session):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )

        exp = payload.get("exp")
        user_tenant_id = payload.get("user_tenant_id")

        if user_tenant_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

        token_tenant_id = payload.get("tenant_id")
        if token_tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token sin tenant asociado",
            )

        set_rls_tenant(db, token_tenant_id)

        user_tenant = (
            db.query(UserTenantDB)
            .join(TenantDB, UserTenantDB.tenant_id == TenantDB.id)
            .filter(
                UserTenantDB.id == user_tenant_id,
                UserTenantDB.status == 1,
                TenantDB.status == 1,
            )
            .first()
        )

        if user_tenant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

        if user_tenant.tenant_id != token_tenant_id:
            logger.warning(
                "Inconsistencia tenant JWT usuario_tenant=%s token_tenant=%s",
                user_tenant.tenant_id,
                token_tenant_id,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="El tenant del token no coincide con el usuario",
            )

        now = int(datetime.now(timezone.utc).timestamp())
        remaining_seconds = exp - now if exp else None

        return {
            "valid": True,
            "expiration": exp,
            "now": now,
            "remaining_seconds": remaining_seconds,
            "remaining_minutes_rounded": (
                math.ceil(remaining_seconds / 60) if remaining_seconds is not None else None
            ),
            "user": {"dni": user_tenant.user.dni, "email": user_tenant.email},
            "tenant": {"id": user_tenant.tenant.id, "slug": user_tenant.tenant.slug},
            "user_tenant_id": user_tenant.id,
        }

    except HTTPException:
        raise
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        ) from exc
