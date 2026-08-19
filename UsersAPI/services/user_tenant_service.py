from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..logging_config import logger
from ..models import UserDB, TenantDB, UserTenantDB
from ..repositories.user_repository import UserRepository
from ..repositories.tenant_repository import TenantRepository
from ..repositories.user_tenant_repository import UserTenantRepository


def create_user_tenant(
    user_id: int,
    tenant_id: int,
    db: Session,
    current_user: UserDB | None = None,
) -> UserTenantDB:

    user_repo = UserRepository(db)
    tenant_repo = TenantRepository(db)
    repo = UserTenantRepository(db)

    # ============================================================
    # VALIDAR USUARIO
    # ============================================================

    usuario = user_repo.get_by_id_including_deleted(user_id)

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no existe",
        )

    if usuario.status == 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario está eliminado. Debe gestionarse primero el usuario.",
        )

    if usuario.status != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario está inactivo. Debe activarse primero el usuario.",
        )

    # ============================================================
    # VALIDAR TENANT
    # ============================================================

    tenant = tenant_repo.get_by_id_including_deleted(tenant_id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El tenant no existe",
        )

    if tenant.status == 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tenant está eliminado. Debe gestionarse primero el tenant.",
        )

    if tenant.status != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tenant está inactivo. Debe activarse primero el tenant.",
        )

    # ============================================================
    # VALIDAR ASOCIACIÓN EXISTENTE
    # ============================================================

    existente: UserTenantDB | None = (
        db.query(UserTenantDB)
        .filter(
            UserTenantDB.user_id == user_id,
            UserTenantDB.tenant_id == tenant_id,
        )
        .first()
    )

    if existente is not None:

        # --------------------------------------------------------
        # Asociación eliminada -> reactivar
        # --------------------------------------------------------

        if existente.status == 3:

            existente.status = 1
            existente.updated_at = datetime.now()
            existente.updated_by = (
                current_user.email
                if current_user
                else "bootstrap"
            )

            try:

                actualizado = repo.update(existente)

                logger.info(
                    "Asociación usuario-tenant reactivada",
                    extra={
                        "user_tenant_id": actualizado.id,
                        "user_id": user_id,
                        "tenant_id": tenant_id,
                    },
                )

                return actualizado

            except Exception as exc:

                db.rollback()

                logger.error(
                    "Error al reactivar asociación usuario-tenant: %s",
                    exc,
                )

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error interno al reactivar la asociación",
                ) from exc

        # --------------------------------------------------------
        # Asociación ya activa
        # --------------------------------------------------------

        if existente.status == 1:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario ya está asociado a este tenant",
            )

        # --------------------------------------------------------
        # Otro estado
        # --------------------------------------------------------

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La asociación usuario-tenant no puede ser creada en su estado actual",
        )

    # ============================================================
    # CREAR ASOCIACIÓN
    # ============================================================

    nueva_asociacion = UserTenantDB(
        user_id=user_id,
        tenant_id=tenant_id,
        status=1,
        created_at=datetime.now(),
        created_by=(
            current_user.email
            if current_user
            else "bootstrap"
        ),
    )

    try:

        creada = repo.add(nueva_asociacion)

        logger.info(
            "Usuario asociado a tenant",
            extra={
                "user_tenant_id": creada.id,
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )

        return creada

    except IntegrityError:

        db.rollback()

        logger.warning(
            "Intento de crear asociación duplicada",
            extra={
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya está asociado a este tenant",
        ) from None

    except Exception as exc:

        db.rollback()

        logger.error(
            "Error inesperado al crear asociación usuario-tenant: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear la asociación",
        ) from exc


def get_user_tenant(
    user_tenant_id: int,
    db: Session,
) -> UserTenantDB:

    repo = UserTenantRepository(db)

    asociacion = repo.get_by_id(user_tenant_id)

    if asociacion is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asociación usuario-tenant no encontrada",
        )

    return asociacion


def list_user_tenants(
    user_id: int,
    db: Session,
):

    user_repo = UserRepository(db)
    repo = UserTenantRepository(db)

    usuario = user_repo.get_by_id_including_deleted(user_id)

    if usuario is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no existe",
        )

    if usuario.status == 3:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario está eliminado. Debe gestionarse primero el usuario.",
        )

    if usuario.status != 1:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario está inactivo. Debe activarse primero el usuario.",
        )

    return repo.get_by_user(user_id)


def list_tenant_users(
    tenant_id: int,
    db: Session,
):

    tenant_repo = TenantRepository(db)
    repo = UserTenantRepository(db)

    tenant = tenant_repo.get_by_id_including_deleted(tenant_id)

    if tenant is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El tenant no existe",
        )

    if tenant.status == 3:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tenant está eliminado. Debe gestionarse primero el tenant.",
        )

    if tenant.status != 1:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tenant está inactivo. Debe activarse primero el tenant.",
        )

    return repo.get_by_tenant(tenant_id)


def delete_user_tenant(
    user_tenant_id: int,
    db: Session,
):

    repo = UserTenantRepository(db)

    asociacion = repo.get_by_id(user_tenant_id)

    if asociacion is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asociación usuario-tenant no encontrada",
        )

    repo.delete(asociacion)

    logger.info(
        "Asociación usuario-tenant eliminada",
        extra={
            "user_tenant_id": asociacion.id,
            "user_id": asociacion.user_id,
            "tenant_id": asociacion.tenant_id,
        },
    )

    return {
        "id": asociacion.id,
        "user_id": asociacion.user_id,
        "tenant_id": asociacion.tenant_id,
        "status": asociacion.status,
        "message": "Asociación usuario-tenant eliminada correctamente",
    }
