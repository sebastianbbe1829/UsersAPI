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
    PermissionDB,
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
from ..security.permission_definitions import PERMISSIONS


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

    ahora = datetime.now()

    # ========================================================
    # 1. VALIDAR TENANT
    # ========================================================

    existing_tenant = tenant_repository.get_by_slug(tenant_slug)

    if existing_tenant is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El tenant ya existe.",
        )

    # ========================================================
    # 2. BUSCAR USUARIO GLOBAL
    # ========================================================

    existing_user = user_repository.get_by_dni(admin_dni)

    if existing_user is not None:
        user = existing_user
    else:
        user = UserDB(
            dni=admin_dni,
            name=admin_name,
            created_at=ahora,
            created_by=admin_dni,
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

    try:
        tenant = tenant_repository.add(tenant)

        if existing_user is None:
            user = user_repository.add(user)

        # ====================================================
        # 4. GARANTIZAR PERMISOS BASE DEL SISTEMA
        #
        # Bootstrap debe poder inicializar una BD limpia. Los
        # permisos son datos de catálogo global y no pertenecen
        # a ningún tenant.
        #
        # Si un permiso existe pero está inactivo, no lo
        # reactivamos silenciosamente: es una configuración
        # administrativa que debe resolverse explícitamente.
        # ====================================================

        permissions_by_code = {}

        for permission_code, permission_name, description in PERMISSIONS:
            permission = permission_repository.get_by_code_any_status(
                permission_code
            )

            if permission is None:
                permission = permission_repository.create(
                    PermissionDB(
                        code=permission_code,
                        name=permission_name,
                        description=description,
                        status=1,
                        created_by="SYSTEM",
                    )
                )

            elif permission.status != 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"El permiso '{permission_code}' "
                        "existe pero está inactivo."
                    ),
                )

            permissions_by_code[permission_code] = permission

        # ====================================================
        # 5. CREAR TOKEN DE ACTIVACIÓN
        # ====================================================

        activation_token = str(uuid.uuid4())

        # ====================================================
        # 6. CREAR ASOCIACIÓN USUARIO - TENANT
        # ====================================================

        user_tenant = UserTenantDB(
            user_id=user.id,
            tenant_id=tenant.id,
            email=admin_email,
            password=get_password_hash(admin_password),
            phone=admin_phone,
            activation_token=activation_token,
            status=0,
            created_at=ahora,
            created_by=admin_dni,
        )

        user_tenant = user_tenant_repository.add(user_tenant)

        # ====================================================
        # 7. CREAR ROL AUTHENTICATE DEL TENANT
        # ====================================================

        authenticate_role = RoleDB(
            tenant_id=tenant.id,
            code="AUTHENTICATE",
            name="Autenticación",
            description="Permite autenticarse en el tenant",
            status=1,
            created_at=ahora,
            created_by=admin_dni,
        )

        authenticate_role = role_repository.add(authenticate_role)

        authenticate_role_permission = RolePermissionDB(
            role_id=authenticate_role.id,
            permission_id=permissions_by_code["AUTHENTICATE"].id,
        )

        role_permission_repository.add(authenticate_role_permission)

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

        admin_role = role_repository.add(admin_role)

        # ====================================================
        # 9. ASOCIAR USUARIO AL ROL ADMIN
        # ====================================================

        user_tenant_role = UserTenantRoleDB(
            user_tenant_id=user_tenant.id,
            role_id=admin_role.id,
        )

        user_tenant_role_repository.add(user_tenant_role)

        # ====================================================
        # 10. ASOCIAR TODOS LOS PERMISOS AL ROL ADMIN
        # ====================================================

        for permission_code, _, _ in PERMISSIONS:
            role_permission_repository.add(
                RolePermissionDB(
                    role_id=admin_role.id,
                    permission_id=permissions_by_code[permission_code].id,
                )
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
                "No fue posible completar el bootstrap porque existe "
                "información duplicada o incompatible."
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
    # 11. EMAIL DE ACTIVACIÓN
    # ========================================================

    try:
        send_email(
            recipient=user_tenant.email,
            subject="Activa tu cuenta en UsersAPI",
            message=(
                f"Hola {user.name},\n\n"
                "Tu cuenta de administrador ha sido creada correctamente.\n\n"
                "Para activar tu cuenta utiliza el siguiente enlace de activación:\n\n"
                f"/users/activate/{user.dni}/{user_tenant.activation_token}\n\n"
                "Este enlace es de un solo uso."
            ),
            dni=user.dni,
            token=user_tenant.activation_token,
            tenant_slug=tenant_slug,
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
            "Bootstrap realizado pero falló el envío del correo de activación: %s",
            exc,
            extra={
                "tenant_id": tenant.id,
                "user_id": user.id,
                "dni": user.dni,
                "email": user_tenant.email,
            },
        )

    # ========================================================
    # 12. WHATSAPP
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
                    "Bootstrap realizado correctamente, pero WhatsApp no pudo ser enviado",
                    extra={
                        "tenant_id": tenant.id,
                        "user_id": user.id,
                        "dni": user.dni,
                        "phone": user_tenant.phone,
                    },
                )

    except Exception as exc:
        logger.warning(
            "Bootstrap realizado pero falló el envío de WhatsApp: %s",
            exc,
            extra={
                "tenant_id": tenant.id,
                "user_id": user.id,
                "dni": user.dni,
                "phone": user_tenant.phone,
            },
        )

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

    return {
        "tenant": tenant,
        "user": user,
        "user_tenant": user_tenant,
        "role": admin_role,
    }
