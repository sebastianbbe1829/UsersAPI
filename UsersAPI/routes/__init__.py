from .user_routes import user_routes
from .auth_routes import auth_routers
from .global_auth_routes import global_auth_routes
from .tenant_routes import tenant_routes
from .tenant_config_routes import tenant_config_routes
from .user_tenant_routes import user_tenant_routes
from .role_routes import role_routes
from .user_tenant_role_routes import user_tenant_role_routes
from .role_permission_routes import role_permission_routes
from .bootstrap_tenant_routes import bootstrap_tenant_routes
from .permission_routes import permission_routes
from .email_routes import email_routes


__all__ = [
    "user_routes",
    "auth_routers",
    "global_auth_routes",
    "tenant_routes",
    "tenant_config_routes",
    "user_tenant_routes",
    "role_routes",
    "user_tenant_role_routes",
    "role_permission_routes",
    "bootstrap_tenant_routes",
    "permission_routes",
    "email_routes",
]
