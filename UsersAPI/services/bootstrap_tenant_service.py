import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..services.auth_service import get_password_hash
from ..logging_config import logger
from ..models import (
    TenantDB,
    TenantConfigDB,
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