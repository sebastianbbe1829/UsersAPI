import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT, HTTP_500_INTERNAL_SERVER_ERROR

from .database import engine
from .routes import (
    user_routes, auth_routers, global_auth_routes, tenant_routes,
    tenant_config_routes, tenant_config_public_routes, user_tenant_routes,
    role_routes, user_tenant_role_routes, role_permission_routes,
    bootstrap_tenant_routes, permission_routes, email_routes, extinguisher_routes,
)
from .logging_config import logger
from fastapi.middleware.cors import CORSMiddleware

CURRENT_FILE = os.path.abspath(__file__)
PACKAGE_DIR = os.path.dirname(CURRENT_FILE)
PROJECT_DIR = os.path.dirname(PACKAGE_DIR)
STATIC_DIR = os.path.join(PROJECT_DIR, "static")
LOGO_PATH = os.path.join(STATIC_DIR, "logo.png")

logger.info("==========================================")
logger.info("CONFIGURACIÓN DE ARCHIVOS ESTÁTICOS")
logger.info("==========================================")
logger.info(f"CURRENT_FILE: {CURRENT_FILE}")
logger.info(f"PACKAGE_DIR: {PACKAGE_DIR}")
logger.info(f"PROJECT_DIR: {PROJECT_DIR}")
logger.info(f"STATIC_DIR: {STATIC_DIR}")
logger.info(f"LOGO_PATH: {LOGO_PATH}")
logger.info(f"STATIC_EXISTS: {os.path.isdir(STATIC_DIR)}")
logger.info(f"LOGO_EXISTS: {os.path.isfile(LOGO_PATH)}")
logger.info("==========================================")

app = FastAPI(
    title="UsersAPI",
    description="API para gestionar usuarios y funcionalidades multi-tenant.",
    version="1.0.0",
    contact={"name": "Sebastian Buitrago Betancur", "email": "sebastianbbe@gmail.com"},
    swagger_ui_parameters={
        "docExpansion": "none", "displayRequestDuration": True,
        "defaultModelsExpandDepth": 0, "defaultModelExpandDepth": 1,
        "filter": True, "syntaxHighlight": True, "persistAuthorization": True,
        "tryItOutEnabled": True, "deepLinking": True,
    },
    openapi_tags=[
        {"name": "Usuarios", "description": "Operaciones sobre usuarios"},
        {"name": "Autenticación", "description": "Autenticación de usuarios y generación de tokens JWT"},
        {"name": "Autenticación SUPER", "description": "Autenticación global del usuario SUPER con MFA"},
        {"name": "Tenants", "description": "Operaciones sobre tenants"},
        {"name": "Configuración UI", "description": "Configuración visual parametrizable por tenant"},
        {"name": "Usuarios - Tenants", "description": "Gestión de asociaciones entre usuarios y tenants"},
        {"name": "Roles", "description": "Operaciones sobre roles"},
        {"name": "Usuarios - Roles", "description": "Gestión de asociaciones entre usuarios y roles"},
        {"name": "Roles - Permisos", "description": "Gestión de permisos asociados a roles"},
        {"name": "Bootstrap", "description": "Inicialización de tenants y configuración inicial del sistema"},
        {"name": "Permisos", "description": "Operaciones sobre permisos"},
        {"name": "Email", "description": "Pruebas administrativas de correo transaccional"},
        {"name": "Extintores", "description": "Inventario y gestión de extintores por tenant"},
    ],
)

origins = ["http://localhost:5173", "https://gestion-usuarios.sebastianbbe.workers.dev"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
else:
    logger.error(f"NO SE ENCONTRÓ EL DIRECTORIO STATIC: {STATIC_DIR}")

app.include_router(user_routes)
app.include_router(auth_routers)
app.include_router(global_auth_routes)
app.include_router(tenant_routes)
app.include_router(tenant_config_routes)
app.include_router(tenant_config_public_routes)
app.include_router(user_tenant_routes)
app.include_router(role_routes)
app.include_router(user_tenant_role_routes)
app.include_router(role_permission_routes)
app.include_router(bootstrap_tenant_routes)
app.include_router(permission_routes)
app.include_router(email_routes)
app.include_router(extinguisher_routes)

@app.get("/", include_in_schema=False)
def root():
    return {"status": "ok", "service": "UsersAPI"}

@app.head("/", include_in_schema=False)
def root_head():
    return

@app.get("/health", include_in_schema=False)
def health():
    return {"status": "healthy", "service": "UsersAPI"}

@app.head("/health", include_in_schema=False)
def health_head():
    return

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errores = []
    for error in exc.errors():
        error = dict(error)
        if "input" in error:
            error["input"] = str(error["input"])
        if "ctx" in error:
            error["ctx"] = {key: str(value) for key, value in error["ctx"].items()}
        errores.append(error)
    return JSONResponse(status_code=HTTP_422_UNPROCESSABLE_CONTENT, content={"detail": errores})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Error no controlado en %s", request.url.path)
    return JSONResponse(status_code=HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "Error interno del servidor"})
