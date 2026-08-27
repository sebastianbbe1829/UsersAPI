from typing import cast

from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ..controllers.auth_controller import get_current_user
from ..database import get_db, set_rls_tenant
from ..models import GlobalUserDB, TenantDB, UserTenantDB
from ..services.auth_service import oauth2_scheme
from ..settings import settings


def get_current_tenant(
    current_user: UserTenantDB | GlobalUserDB = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserTenantDB:

    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no autenticado",
        )

    # ========================================================
    # USUARIO SUPER
    #
    # El SUPER es una identidad global. El contexto del tenant
    # se obtiene exclusivamente del JWT SUPER y se valida contra
    # la base de datos antes de establecer RLS.
    #
    # Se devuelve una relación activa del tenant únicamente para
    # conservar el contrato actual de los servicios, que esperan
    # un UserTenantDB para resolver tenant_id.
    # ========================================================

    if isinstance(current_user, GlobalUserDB):

        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm],
            )
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No se pudo validar el contexto SUPER",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        if payload.get("user_type") != "SUPER":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Contexto de autenticación inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )

        tenant_id = payload.get("tenant_id")
        tenant_slug = payload.get("tenant_slug")

        if tenant_id is None or tenant_slug is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="El token SUPER no contiene contexto de tenant",
                headers={"WWW-Authenticate": "Bearer"},
            )

        tenant = (
            db.query(TenantDB)
            .filter(
                TenantDB.id == tenant_id,
                TenantDB.slug == tenant_slug,
                TenantDB.status == 1,
            )
            .first()
        )

        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El tenant no está activo",
            )

        user_tenant = (
            db.query(UserTenantDB)
            .filter(
                UserTenantDB.tenant_id == tenant.id,
                UserTenantDB.status == 1,
            )
            .first()
        )

        if user_tenant is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El tenant no tiene usuarios activos",
            )

        set_rls_tenant(
            db=db,
            tenant_id=cast(int, tenant.id),
        )

        return user_tenant

    # ========================================================
    # USUARIO NORMAL
    # ========================================================

    user_status = cast(
        int,
        current_user.status,
    )

    if user_status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no está activo en el tenant",
        )

    tenant_status = cast(
        int,
        current_user.tenant.status,
    )

    if tenant_status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El tenant no está activo",
        )

    # ========================================================
    # ESTABLECER CONTEXTO RLS
    # ========================================================

    tenant_id = cast(
        int,
        current_user.tenant_id,
    )

    set_rls_tenant(
        db=db,
        tenant_id=tenant_id,
    )

    return current_user