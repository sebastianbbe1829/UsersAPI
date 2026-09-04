from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..logging_config import logger
from ..models import (
    UserDB,
    UserTenantDB,
    RoleDB,
    UserTenantRoleDB,
)
from ..repositories.user_tenant_role_repository import (
    UserTenantRoleRepository,
)


# ============================================================
# ASIGNAR ROL A USUARIO
# ============================================================

def assign_role_to_user(
    user_tenant_id: int,
    role_id: int,
    tenant_id: int,
    db: Session,
    current_user: UserDB | None = None,
) -> UserTenantRoleDB:

    repo = UserTenantRoleRepository(db)

    # ============================================================
    # 1. VALIDAR RELACIÓN USUARIO-TENANT
    # ============================================================

    user_tenant = (
        db.query(UserTenantDB)
        .filter(
            UserTenantDB.id == user_tenant_id,
            UserTenantDB.tenant_id == tenant_id,
            UserTenantDB.status == 1,
        )
        .first()
    )

    if not user_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La relación usuario-tenant no existe",
        )

    # ============================================================
    # 2. VALIDAR USUARIO GLOBAL
    #
    # UserDB NO tiene status.
    # ============================================================

    user = (
        db.query(UserDB)
        .filter(
            UserDB.id == user_tenant.user_id,
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no existe",
        )

    # ============================================================
    # 3. VALIDAR ROL
    # ============================================================

    role = (
        db.query(RoleDB)
        .filter(
            RoleDB.id == role_id,
            RoleDB.tenant_id == tenant_id,
            RoleDB.status == 1,
        )
        .first()
    )

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El rol no existe en el tenant seleccionado",
        )

    # ============================================================
    # 4. VALIDAR SI YA ESTÁ ASIGNADO
    # ============================================================

    existente = repo.get_by_user_tenant_and_role(
        user_tenant_id=user_tenant_id,
        role_id=role_id,
    )

    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya tiene asignado este rol",
        )

    # ============================================================
    # 5. CREAR ASIGNACIÓN
    # ============================================================

    nueva_asignacion = UserTenantRoleDB(
        user_tenant_id=user_tenant_id,
        role_id=role_id,
    )

    try:

        creada = repo.add(nueva_asignacion)

        logger.info(
            "Rol asignado a usuario",
            extra={
                "user_tenant_role_id": creada.id,
                "user_tenant_id": user_tenant_id,
                "user_id": user.id,
                "role_id": role_id,
                "tenant_id": tenant_id,
            },
        )

        return creada

    except IntegrityError:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya tiene asignado este rol",
        ) from None

    except Exception as exc:

        db.rollback()

        logger.error(
            "Error inesperado al asignar rol: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al asignar rol",
        ) from exc

# ============================================================
# LISTAR ROLES DE UN USUARIO
# ============================================================

def list_user_roles(
    user_tenant_id: int,
    tenant_id: int,
    db: Session,
):

    # ============================================================
    # 1. VALIDAR RELACIÓN USUARIO-TENANT
    # ============================================================

    user_tenant = (
        db.query(UserTenantDB)
        .filter(
            UserTenantDB.id == user_tenant_id,
            UserTenantDB.tenant_id == tenant_id,
            UserTenantDB.status == 1,
        )
        .first()
    )

    if not user_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La relación usuario-tenant no existe",
        )

    # ============================================================
    # 2. VALIDAR QUE EL USUARIO GLOBAL EXISTA
    # ============================================================

    user = (
        db.query(UserDB)
        .filter(
            UserDB.id == user_tenant.user_id,
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no existe o está eliminado",
        )

    # ============================================================
    # 3. LISTAR ROLES
    # ============================================================

    repo = UserTenantRoleRepository(db)

    return repo.get_all_by_user_tenant(
        user_tenant_id=user_tenant_id,
    )


# ============================================================
# ELIMINAR ROL DE USUARIO
# ============================================================

def delete_user_role(
    user_tenant_role_id: int,
    tenant_id: int,
    db: Session,
):

    repo = UserTenantRoleRepository(db)

    # ============================================================
    # 1. BUSCAR ASIGNACIÓN
    # ============================================================

    asignacion = repo.get_by_id(
        user_tenant_role_id=user_tenant_role_id,
    )

    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La asignación de rol no existe",
        )

    # ============================================================
    # 2. VALIDAR RELACIÓN USUARIO-TENANT
    # ============================================================

    user_tenant = (
        db.query(UserTenantDB)
        .filter(
            UserTenantDB.id == asignacion.user_tenant_id,
            UserTenantDB.tenant_id == tenant_id,
            UserTenantDB.status == 1,
        )
        .first()
    )

    if not user_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La asignación de rol no pertenece al tenant",
        )

    # ============================================================
    # 3. VALIDAR QUE EL USUARIO GLOBAL EXISTA
    # ============================================================

    user = (
        db.query(UserDB)
        .filter(
            UserDB.id == user_tenant.user_id,
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no existe o está eliminado",
        )

    # ============================================================
    # 4. VALIDAR QUE EL ROL PERTENEZCA AL TENANT
    # ============================================================

    role = (
        db.query(RoleDB)
        .filter(
            RoleDB.id == asignacion.role_id,
            RoleDB.tenant_id == tenant_id,
            RoleDB.status == 1,
        )
        .first()
    )

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El rol no pertenece al tenant seleccionado",
        )

    # ============================================================
    # 5. ELIMINAR ASIGNACIÓN
    # ============================================================

    repo.delete(asignacion)

    logger.info(
        "Rol removido del usuario",
        extra={
            "user_tenant_role_id": asignacion.id,
            "user_tenant_id": asignacion.user_tenant_id,
            "user_id": user.id,
            "role_id": asignacion.role_id,
            "tenant_id": tenant_id,
        },
    )

    return {
        "id": asignacion.id,
        "user_tenant_id": asignacion.user_tenant_id,
        "role_id": asignacion.role_id,
        "message": "Rol eliminado correctamente",
    }