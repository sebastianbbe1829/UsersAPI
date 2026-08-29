from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..schemas import BootstrapTenantRequest, BootstrapTenantResponse
from ..services.bootstrap_tenant_service import bootstrapTenant


def bootstrap_tenant_application(
    datos: BootstrapTenantRequest,
    db: Session,
) -> BootstrapTenantResponse:

    try:

        result = bootstrapTenant(
            db=db,
            tenant_name=datos.tenant_name,
            tenant_slug=datos.tenant_slug,
            admin_dni=datos.admin_dni,
            admin_name=datos.admin_name,
            admin_email=datos.admin_email,
            admin_password=datos.admin_password,
            admin_phone=datos.admin_phone,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno durante el bootstrap.",
        ) from exc

    # ========================================================
    # EXTRAER RESULTADO
    # ========================================================

    tenant = result["tenant"]
    user = result["user"]
    user_tenant = result["user_tenant"]
    role = result["role"]

    # ========================================================
    # RESPUESTA
    #
    # MANTENEMOS EXACTAMENTE LA ESTRUCTURA
    # DE BootstrapResponse
    # ========================================================

    return BootstrapTenantResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,

        user_id=user.id,
        user_dni=user.dni,
        user_name=user.name,

        user_tenant_id=user_tenant.id,
        user_email=user_tenant.email,

        role_id=role.id,
        role_code=role.code,
        role_name=role.name,

        message="Bootstrap realizado correctamente.",
    )