from sqlalchemy.orm import Session

from UsersAPI.util.excel_utils import export_to_excel

from ..logging_config import logger
from ..models import GlobalUserDB, UserTenantDB
from ..repositories.user_repository import UserRepository
from ..repositories.user_tenant_repository import UserTenantRepository
from .user_service_helpers import _tenant_link


def export_users(
    db: Session,
    current_user: UserTenantDB | GlobalUserDB,
    tenant_id: int,
):
    user_repository = UserRepository(db)
    user_tenant_repository = UserTenantRepository(db)
    users = user_repository.get_all_by_tenant(tenant_id, None)
    data = []
    for user in users:
        link = _tenant_link(user, tenant_id, user_tenant_repository)
        data.append(
            {
                "DNI": user.dni,
                "Nombre": user.name,
                "Email": link.email,
                "Teléfono": link.phone or "",
                "Estado": "Activo" if link.status == 1 else "Inactivo",
            }
        )
    logger.debug(
        "Usuarios exportados",
        extra={"tenant_id": tenant_id, "cantidad": len(data)},
    )
    return export_to_excel(
        data=data,
        filename="usuarios.xlsx",
        current_user=current_user,
    )
