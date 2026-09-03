from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import set_rls_tenant
from ..logging_config import logger
from ..models import UserDB, UserTenantDB
from ..repositories.user_repository import UserRepository
from ..repositories.user_tenant_repository import UserTenantRepository
from .user_service_helpers import _user_payload


def activate_user(
    dni: str,
    token: str,
    db: Session,
):
    tenant_id = db.execute(
        text(
            """
            SELECT users_api.resolve_tenant_id_by_activation_token(
                :activation_token
            )
            """
        ),
        {
            "activation_token": token,
        },
    ).scalar()

    if tenant_id is None:
        logger.warning(
            "Intento de activación con token inválido",
            extra={"dni": dni},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de activación inválido",
        )

    set_rls_tenant(db, tenant_id)

    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)

    usuario = user_repository.get_by_dni(dni)

    if usuario is None:
        logger.warning(
            "Intento de activación para usuario inexistente",
            extra={"dni": dni},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    link = user_tenant_repository.get_by_activation_token(token)

    if link is None:
        logger.warning(
            "Intento de activación con token inválido",
            extra={"dni": dni},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de activación inválido",
        )

    if link.user_id != usuario.id:
        logger.warning(
            "Intento de activación con token perteneciente a otro usuario",
            extra={
                "dni": dni,
                "user_id": usuario.id,
                "token_user_id": link.user_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de activación inválido",
        )

    if link.status == 3:
        logger.warning(
            "Intento de activar usuario eliminado",
            extra={"dni": dni, "user_tenant_id": link.id},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario se encuentra eliminado",
        )

    if link.status == 1:
        logger.info(
            "Intento de activar usuario que ya estaba activo",
            extra={"dni": dni, "user_tenant_id": link.id},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario ya se encuentra activo",
        )

    link.status = 1
    link.activation_token = None

    ahora = datetime.now()
    link.updated_at = ahora
    link.updated_by = "activation"
    usuario.updated_at = ahora
    usuario.updated_by = "activation"

    try:
        user_tenant_repository.update(link)
        user_repository.update(usuario)
    except IntegrityError as exc:
        logger.exception(
            "Error de integridad al activar usuario",
            extra={
                "dni": dni,
                "user_tenant_id": link.id,
                "error": str(exc),
                "orig": str(exc.orig),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fue posible activar el usuario",
        ) from exc
    except Exception as exc:
        logger.exception(
            "Error inesperado al activar usuario",
            extra={
                "dni": dni,
                "user_tenant_id": link.id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al activar usuario",
        ) from exc

    logger.info(
        "Usuario activado correctamente",
        extra={
            "dni": dni,
            "user_id": usuario.id,
            "user_tenant_id": link.id,
        },
    )

    return _user_payload(
        usuario,
        link,
        message="Usuario activado correctamente",
    )
