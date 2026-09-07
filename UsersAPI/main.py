from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from UsersAPI.database import Base, engine
from UsersAPI.logging_config import setup_logging
from UsersAPI.domains.core.routes import (
    auth_routes,
    bootstrap_tenant_routes,
    diagnostics_routes,
    email_routes,
    extinguisher_inspection_item_routes,
    extinguisher_inspection_routes,
    extinguisher_routes,
    extinguisher_type_routes,
    global_auth_routes,
    global_user_routes,
    otp_routes,
    password_recovery_routes,
    permission_routes,
    role_permission_routes,
    role_routes,
    super_tenant_routes,
    tenant_config_public_routes,
    tenant_config_routes,
    tenant_routes,
    user_routes,
    user_tenant_role_routes,
    user_tenant_routes,
)
from UsersAPI.domains.clients.routes import (
    catalog_routes,
    client_routes,
    screening_routes,
)

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Users API",
    description="API multi-tenant para gestión de usuarios, clientes y recursos empresariales.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters={
        "defaultModelExpandDepth": 1,
        "filter": True,
        "syntaxHighlight": True,
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
        {
            "name": "Usuarios SUPER",
            "description": "Administración global de usuarios SUPER",
        },
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
        {
            "name": "OTP",
            "description": "Generación y validación de códigos OTP temporales",
        },
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
    ],
)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_routes.router)
app.include_router(auth_routes.router)
app.include_router(bootstrap_tenant_routes.router)
app.include_router(diagnostics_routes.router)
app.include_router(email_routes.router)
app.include_router(extinguisher_routes.router)
app.include_router(extinguisher_type_routes.router)
app.include_router(extinguisher_inspection_routes.router)
app.include_router(extinguisher_inspection_item_routes.router)
app.include_router(global_auth_routes.router)
app.include_router(global_user_routes.router)
app.include_router(otp_routes.router)
app.include_router(password_recovery_routes.router)
app.include_router(permission_routes.router)
app.include_router(role_permission_routes.router)
app.include_router(role_routes.router)
app.include_router(super_tenant_routes.router)
app.include_router(tenant_config_public_routes.router)
app.include_router(tenant_config_routes.router)
app.include_router(tenant_routes.router)
app.include_router(user_tenant_routes.router)
app.include_router(user_tenant_role_routes.router)
app.include_router(catalog_routes.router)
app.include_router(client_routes.router)
app.include_router(screening_routes.router)
