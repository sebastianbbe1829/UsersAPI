from .user_routes import user_routes
from .auth_routes import auth_routers
from .tenant_routes import tenant_routes
from .user_tenant_routes import user_tenant_routes


__all__ = [
    "user_routes",
    "auth_routers",
    "tenant_routes",
    "user_tenant_routes",
]