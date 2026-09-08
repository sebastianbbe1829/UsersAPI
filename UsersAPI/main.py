from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from UsersAPI.config import settings
from UsersAPI.domains.auth.routes.auth_routes import router as auth_router
from UsersAPI.domains.auth.routes.password_recovery_routes import router as password_recovery_router
from UsersAPI.domains.auth.routes.super_auth_routes import router as super_auth_router
from UsersAPI.domains.auth.routes.otp_routes import router as otp_router
from UsersAPI.domains.clients.routes.catalog_routes import router as client_catalog_router
from UsersAPI.domains.clients.routes.client_routes import router as client_router
from UsersAPI.domains.clients.routes.screening_routes import router as screening_router
from UsersAPI.domains.core.database import engine
from UsersAPI.domains.email.routes.email_routes import router as email_router
from UsersAPI.domains.extinguishers.routes.extinguisher_routes import router as extinguisher_router
from UsersAPI.domains.extinguishers.routes.extinguisher_type_routes import router as extinguisher_type_router
from UsersAPI.domains.extinguishers.routes.inspection_item_routes import router as inspection_item_router
from UsersAPI.domains.extinguishers.routes.inspection_routes import router as inspection_router
from UsersAPI.domains.inventory.routes.inventory_routes import router as inventory_router
from UsersAPI.domains.permissions.routes.permission_routes import router as permission_router
from UsersAPI.domains.roles.routes.role_permission_routes import router as role_permission_router
from UsersAPI.domains.roles.routes.role_routes import router as role_router
from UsersAPI.domains.tenants.routes.tenant_routes import router as tenant_router
from UsersAPI.domains.tenants.routes.user_tenant_routes import router as user_tenant_router
from UsersAPI.domains.tenants.routes.user_tenant_role_routes import router as user_tenant_role_router
from UsersAPI.domains.ui_config.routes.ui_config_routes import router as ui_config_router
from UsersAPI.domains.users.routes.user_routes import router as user_router
from UsersAPI.domains.users_super.routes.super_user_routes import router as super_user_router
from UsersAPI.domains.sales.routes.sale_routes import router as sales_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.PROJECT_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={
        "persistAuthorization": True,
        "tryItOutEnabled": True,
        "deepLinking": True,
    },
    openapi_tags=[
        {"name": "Usuarios", "description": "Operaciones sobre usuarios"},
        {
            "name": "Autenticación",
            "description": "Autenticación de usuarios y generación de tokens JWT",
        },
        {
            "name": "Recuperación de contraseña",
            "description": "Recuperación de contraseña mediante OTP",
        },
        {
            "name": "Autenticación SUPER",
            "description": "Autenticación global del usuario SUPER con MFA",
        },
        {"name": "Usuarios SUPER", "description": "Administración global de usuarios SUPER"},
        {"name": "Tenants", "description": "Operaciones sobre tenants"},
        {
            "name": "Configuración UI",
            "description": "Configuración visual parametrizable por tenant",
        },
        {
            "name": "Usuarios - Tenants",
            "description": "Gestión de asociaciones entre usuarios y tenants",
        },
        {"name": "Roles", "description": "Operaciones sobre roles"},
        {
            "name": "Usuarios - Roles",
            "description": "Gestión de asociaciones entre usuarios y roles",
        },
        {
            "name": "Roles - Permisos",
            "description": "Gestión de permisos asociados a roles",
        },
        {
            "name": "Bootstrap",
            "description": "Inicialización de tenants y configuración inicial del sistema",
        },
        {"name": "Permisos", "description": "Operaciones sobre permisos"},
        {
            "name": "Email",
            "description": "Pruebas administrativas de correo transaccional",
        },
        {"name": "OTP", "description": "Generación y validación de códigos OTP temporales"},
        {
            "name": "Extintores",
            "description": "Inventario y gestión de extintores por tenant",
        },
        {
            "name": "Tipos de extintor",
            "description": "Catálogo global de tipos de extintor",
        },
        {
            "name": "Revisiones de extintores",
            "description": "Histórico y control de revisiones de extintores",
        },
        {
            "name": "Ítems de revisión",
            "description": "Catálogo de ítems utilizados en las revisiones de extintores",
        },
        {"name": "Clientes", "description": "Gestión de clientes por tenant"},
        {
            "name": "Catálogos de clientes",
            "description": "Catálogos de solo lectura utilizados por el dominio de clientes",
        },
        {
            "name": "Clientes - Listas Restrictivas",
            "description": "Screening e histórico de listas restrictivas",
        },
        {
            "name": "Inventarios",
            "description": "Tipos, productos, inventario y movimientos por tenant",
        },
        {
            "name": "Ventas",
            "description": "Ventas, clientes participantes, pagos y descuentos por tenant",
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(password_recovery_router)
app.include_router(super_auth_router)
app.include_router(otp_router)
app.include_router(client_catalog_router)
app.include_router(client_router)
app.include_router(screening_router)
app.include_router(email_router)
app.include_router(extinguisher_router)
app.include_router(extinguisher_type_router)
app.include_router(inspection_item_router)
app.include_router(inspection_router)
app.include_router(inventory_router)
app.include_router(permission_router)
app.include_router(role_permission_router)
app.include_router(role_router)
app.include_router(tenant_router)
app.include_router(user_tenant_router)
app.include_router(user_tenant_role_router)
app.include_router(ui_config_router)
app.include_router(user_router)
app.include_router(super_user_router)
app.include_router(sales_router)
