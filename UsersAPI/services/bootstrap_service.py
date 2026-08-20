import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..controllers.auth_controller import get_password_hash
from ..logging_config import logger
from ..models import (
    TenantDB,
    UserDB,
    UserTenantDB,
    RoleDB,
    UserTenantRoleDB,
    RolePermissionDB,
)
from ..repositories.tenant_repository import TenantRepository
from ..repositories.user_repository import UserRepository
from ..repositories.user_tenant_repository import UserTenantRepository
from ..repositories.role_repository import RoleRepository
from ..repositories.user_tenant_role_repository import (
    UserTenantRoleRepository,
)
from ..repositories.role_permission_repository import (
    RolePermissionRepository,
)
from ..repositories.permission_repository import PermissionRepository
from ..util.email_utils import send_email
from ..util.whatsapp_utils import send_whatsapp


# ============================================================
# PERMISOS DEL ADMINISTRADOR DEL TENANT
# ============================================================

ADMIN_PERMISSION_CODES = (
    "USER_CREATE",
    "USER_READ",
    "USER_UPDATE",
    "USER_DELETE",
)


# ============================================================
# BOOTSTRAP
# ============================================================

def bootstrap(
    db: Session,
    tenant_name: str,
    tenant_slug: str,
    admin_dni: str,
    admin_name: str,
    admin_email: str,
    admin_password: str,
    admin_phone: str | None = None,
):
    tenant_repository = TenantRepository(db)
    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)
    role_repository = RoleRepository(db)
    user_tenant_role_repository = UserTenantRoleRepository(db)
    role_permission_repository = RolePermissionRepository(db)
    permission_repository = PermissionRepository(db)

    # ========================================================
    # FECHA/HORA EXACTA DE ESTA OPERACIÓN
    # ========================================================

    ahora = datetime.now()

    # ========================================================
    # 1. VALIDAR TENANT
    # ========================================================

    existing_tenant = tenant_repository.get_by_slug(
        tenant_slug
    )

    if existing_tenant is not None:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El tenant ya existe.",
        )

    # ========================================================
    # 2. VALIDAR USUARIO GLOBAL
    # ========================================================

    existing_user = user_repository.get_by_dni(
        admin_dni
    )

    if existing_user is not None:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El DNI del administrador ya existe.",
        )

    # ========================================================
    # 3. CREAR TENANT
    # ========================================================

    tenant = TenantDB(
        name=tenant_name,
        slug=tenant_slug,
        status=1,
        created_at=ahora,
        created_by=admin_dni,
    )

    # ========================================================
    # 4. CREAR USUARIO GLOBAL
    # ========================================================
    #
    # IMPORTANTE:
    #
    # NO modificamos UserDB.
    #
    # El created_at se establece aquí explícitamente porque
    # UserDB.created_at es NOT NULL y el modelo ya está estable.
    #

    user = UserDB(
        dni=admin_dni,
        name=admin_name,
        created_at=ahora,
        created_by=admin_dni,
    )

    # ========================================================
    # 5. PERSISTIR TENANT Y USER
    #
    # Necesitamos los IDs generados por PostgreSQL.
    # Los repositories hacen flush().
    # ========================================================

    try:

        tenant = tenant_repository.add(
            tenant
        )

        user = user_repository.add(
            user
        )

        # ====================================================
        # 6. GENERAR TOKEN DE ACTIVACIÓN
        # ====================================================

        activation_token = str(
            uuid.uuid4()
        )

        # ====================================================
        # 7. CREAR ASOCIACIÓN USUARIO - TENANT
        #
        # El administrador queda INACTIVO.
        #
        # 0 = inactivo
        # 1 = activo
        # 3 = eliminado
        #
        # De esta manera debe activar la cuenta mediante
        # el enlace enviado por correo.
        # ====================================================

        user_tenant = UserTenantDB(
            user_id=user.id,
            tenant_id=tenant.id,
            email=admin_email,
            password=get_password_hash(
                admin_password
            ),
            phone=admin_phone,
            activation_token=activation_token,
            status=0,
            created_at=ahora,
            created_by=admin_dni,
        )

        user_tenant = (
            user_tenant_repository.add(
                user_tenant
            )
        )

        # ====================================================
        # 8. CREAR ROL ADMIN DEL TENANT
        # ====================================================

        admin_role = RoleDB(
            tenant_id=tenant.id,
            code="ADMIN",
            name="Administrador",
            description="Administrador del tenant",
            status=1,
            created_at=ahora,
            created_by=admin_dni,
        )

        admin_role = role_repository.add(
            admin_role
        )

        # ====================================================
        # 9. ASOCIAR USUARIO AL ROL ADMIN
        # ====================================================

        user_tenant_role = UserTenantRoleDB(
            user_tenant_id=user_tenant.id,
            role_id=admin_role.id,
        )

        user_tenant_role_repository.add(
            user_tenant_role
        )

        # ====================================================
        # 10. ASOCIAR PERMISOS AL ROL ADMIN
        # ====================================================

        for permission_code in ADMIN_PERMISSION_CODES:

            permission = (
                permission_repository.get_by_code(
                    permission_code
                )
            )

            if permission is None:

                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"El permiso '{permission_code}' "
                        "no existe o está inactivo."
                    ),
                )

            role_permission = RolePermissionDB(
                role_id=admin_role.id,
                permission_id=permission.id,
            )

            role_permission_repository.add(
                role_permission
            )

    except HTTPException:
        raise

    except IntegrityError as exc:

        logger.exception(
            "Error de integridad durante bootstrap",
            extra={
                "tenant_slug": tenant_slug,
                "admin_dni": admin_dni,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No fue posible completar el bootstrap "
                "porque existe información duplicada "
                "o incompatible."
            ),
        ) from exc

    except Exception as exc:

        logger.exception(
            "Error inesperado durante bootstrap",
            extra={
                "tenant_slug": tenant_slug,
                "admin_dni": admin_dni,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno durante el bootstrap.",
        ) from exc

    # ========================================================
    # 11. ENVIAR EMAIL DE ACTIVACIÓN
    # ========================================================
    #
    # IMPORTANTE:
    #
    # El email NO debe provocar rollback del bootstrap.
    #
    # El usuario ya fue creado correctamente.
    # Si el correo falla, solamente registramos el error.
    # ========================================================

    try:

        send_email(
            recipient=user_tenant.email,
            subject="Activa tu cuenta en UsersAPI",
            message=(
                f"Hola {user.name},\n\n"
                "Tu cuenta de administrador ha sido creada "
                "correctamente.\n\n"
                "Para activar tu cuenta utiliza el siguiente "
                "enlace de activación:\n\n"
                f"/users/activate/{user.dni}/"
                f"{user_tenant.activation_token}\n\n"
                "Este enlace es de un solo uso."
            ),
            dni=user.dni,
            token=user_tenant.activation_token,
        )

        logger.info(
            "Correo de activación enviado durante bootstrap",
            extra={
                "tenant_id": tenant.id,
                "user_id": user.id,
                "dni": user.dni,
                "email": user_tenant.email,
            },
        )

    except Exception as exc:

        logger.warning(
            "Bootstrap realizado pero falló el envío "
            "del correo de activación: %s",
            exc,
            extra={
                "tenant_id": tenant.id,
                "user_id": user.id,
                "dni": user.dni,
                "email": user_tenant.email,
            },
        )

    # ========================================================
    # 12. ENVIAR WHATSAPP
    # ========================================================

    try:

        if user_tenant.phone:

            whatsapp_response = send_whatsapp(
                to_number=user_tenant.phone,
                message=None,
                template_name="hello_world",
                parameters=None,
            )

            if whatsapp_response is not None:

                logger.info(
                    "WhatsApp de activación enviado durante bootstrap",
                    extra={
                        "tenant_id": tenant.id,
                        "user_id": user.id,
                        "dni": user.dni,
                        "phone": user_tenant.phone,
                    },
                )

            else:

                logger.warning(
                    "Bootstrap realizado correctamente, "
                    "pero WhatsApp no pudo ser enviado",
                    extra={
                        "tenant_id": tenant.id,
                        "user_id": user.id,
                        "dni": user.dni,
                        "phone": user_tenant.phone,
                    },
                )

        else:

            logger.info(
                "Bootstrap realizado sin teléfono "
                "para envío de WhatsApp",
                extra={
                    "tenant_id": tenant.id,
                    "user_id": user.id,
                    "dni": user.dni,
                },
            )

    except Exception as exc:

        logger.warning(
            "Bootstrap realizado pero falló el envío "
            "de WhatsApp: %s",
            exc,
            extra={
                "tenant_id": tenant.id,
                "user_id": user.id,
                "dni": user.dni,
                "phone": user_tenant.phone,
            },
        )

    # ========================================================
    # 13. LOG FINAL
    # ========================================================

    logger.info(
        "Bootstrap realizado correctamente",
        extra={
            "tenant_id": tenant.id,
            "tenant_slug": tenant.slug,
            "user_id": user.id,
            "dni": user.dni,
            "user_tenant_id": user_tenant.id,
            "role_id": admin_role.id,
        },
    )

    # ========================================================
    # 14. RETORNAR RESULTADO
    #
    # NO COMMIT
    # NO ROLLBACK
    #
    # database.py controla la transacción.
    # ========================================================

    return {
        "tenant": tenant,
        "user": user,
        "user_tenant": user_tenant,
        "role": admin_role,
    }