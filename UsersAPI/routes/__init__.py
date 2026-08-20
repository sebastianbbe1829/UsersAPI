from .user_routes import user_routes
from .auth_routes import auth_routers
from .tenant_routes import tenant_routes
from .user_tenant_routes import user_tenant_routes
from .role_routes import role_routes
from .user_tenant_role_routes import user_tenant_role_routes
from .role_permission_routes import role_permission_routes
from .bootstrap_routes import bootstrap_routes


__all__ = [
    "user_routes",
    "auth_routers",
    "tenant_routes",
    "user_tenant_routes",
    "role_routes",
    "user_tenant_role_routes",
    "role_permission_routes",
    "bootstrap_routes",
]