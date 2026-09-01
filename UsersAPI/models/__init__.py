from .user import UserDB
from .tenant import TenantDB
from .tenant_config import TenantConfigDB
from .user_tenant import UserTenantDB
from .global_user import GlobalUserDB
from .role import RoleDB
from .permission import PermissionDB
from .role_permission import RolePermissionDB
from .user_tenant_role import UserTenantRoleDB
from .extinguisher import ExtinguisherDB
from .extinguisher_type import ExtinguisherTypeDB
from .extinguisher_inspection import ExtinguisherInspectionDB, ExtinguisherInspectionItemDB
from .extinguisher_recharge import ExtinguisherRechargeDB

__all__ = [
    "UserDB", "TenantDB", "TenantConfigDB", "UserTenantDB", "GlobalUserDB", "RoleDB",
    "PermissionDB", "RolePermissionDB", "UserTenantRoleDB", "ExtinguisherDB",
    "ExtinguisherTypeDB", "ExtinguisherInspectionDB", "ExtinguisherInspectionItemDB",
    "ExtinguisherRechargeDB",
]
