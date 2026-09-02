from fastapi import HTTPException, status
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.orm import Session

from ..database import set_rls_tenant
from ..logging_config import logger
from ..models import TenantDB, UserTenantDB
from ..settings import settings


def get_current_user_from_token(
    token: str,
    db: Session,
) -> UserTenantDB:
    """Resolve and validate the active tenant user represented by a JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except JWTError as exc:
        raise credentials_exception from exc

    user_tenant_id = payload.get("user_tenant_id")
    if user_tenant_id is None:
        raise credentials_exception

    token_tenant_id = payload.get("tenant_id")
    if token_tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin tenant asociado",
            headers={"WWW-Authenticate": "Bearer"},
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no pertenece al tenant",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user_tenant.tenant_id != token_tenant_id:
        logger.warning(
            "Inconsistencia tenant JWT usuario_tenant=%s token_tenant=%s",
            user_tenant.tenant_id,
            token_tenant_id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El tenant del token no coincide con el usuario",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_tenant
