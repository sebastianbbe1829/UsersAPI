import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.status import (
    HTTP_422_UNPROCESSABLE_CONTENT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from .routes import (
    auth_routers,
    bootstrap_tenant_routes,
    email_routes,
    extinguisher_inspection_item_routes,
    extinguisher_inspection_routes,
    extinguisher_nested_inspection_routes,
    extinguisher_routes,
    extinguisher_type_routes,
    global_auth_routes,
    global_user_routes,
    otp_routes,
    password_recovery_routes,
    permission_routes,
    role_permission_routes,
    role_routes,
    tenant_config_public_routes,
    tenant_config_routes,
    tenant_routes,
    user_routes,
    user_tenant_role_routes,
    user_tenant_routes,
)
from .routes.diagnostics_routes import router as diagnostics_router
from .logging_config import logger

CURRENT_FILE = os.path.abspath(__file__)
PACKAGE_DIR = os.path.dirname(CURRENT_FILE)
PROJECT_DIR = os.path.dirname(PACKAGE_DIR)
STATIC_DIR = os.path.join(PROJECT_DIR, "static")
LOGO_PATH = os.path.join(STATIC_DIR, "logo.png")

app = FastAPI(
    title="UsersAPI",
    description="API para gestionar usuarios con búsqueda por DNI, usando FastAPI y SQLAlchemy.",
    version="1.0.0",
    contact={"name": "Sebastian Buitrago Betancur", "email": "sebastianbbe@gmail.com"},
    swagger_ui_parameters={
        "docExpansion": "none",
        "displayRequestDuration": True,
        "defaultModelsExpandDepth": 0,
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
    ],
)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://192.168.1.73:5173",
    "https://gestion-usuarios.sebastianbbe.workers.dev",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Tenant-ID",
        "X-Bootstrap-Key",
        "X-Bootstrap-Tenant-Key",
        "X-Super-Bootstrap-Secret",
        "X-Super-MFA-OTP",
        "X-OTP-API-Key",
        "X-Email-Key",
    ],
)
logger.debug("Configuración de CORS establecida para los orígenes: %s", origins)

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
logger.debug("Directorio de archivos estáticos montado en /static: %s", STATIC_DIR)


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


app.include_router(user_routes)
logger.debug("Rutas de usuarios registradas")
app.include_router(auth_routers)
logger.debug("Rutas de autenticación registradas")
app.include_router(password_recovery_routes)
logger.debug("Rutas de recuperación de contraseña registradas")
app.include_router(global_auth_routes)
logger.debug("Rutas de autenticación global registradas")
app.include_router(global_user_routes)
logger.debug("Rutas de administración de usuarios SUPER registradas")
app.include_router(tenant_routes)
logger.debug("Rutas de tenants registradas")
app.include_router(tenant_config_routes)
logger.debug("Rutas de configuración de tenants registradas")
app.include_router(tenant_config_public_routes)
logger.debug("Rutas de configuración pública de tenants registradas")
app.include_router(user_tenant_routes)
logger.debug("Rutas de usuarios en tenants registradas")
app.include_router(role_routes)
logger.debug("Rutas de roles registradas")
app.include_router(user_tenant_role_routes)
logger.debug("Rutas de roles de usuarios en tenants registradas")
app.include_router(role_permission_routes)
logger.debug("Rutas de permisos de roles registradas")
app.include_router(bootstrap_tenant_routes)
logger.debug("Rutas de bootstrap de tenants registradas")
app.include_router(permission_routes)
logger.debug("Rutas de permisos registradas")
app.include_router(email_routes)
logger.debug("Rutas de correos electrónicos registradas")
app.include_router(otp_routes)
logger.debug("Rutas de OTP registradas")
app.include_router(extinguisher_routes)
logger.debug("Rutas de extintores registradas")
app.include_router(extinguisher_type_routes)
logger.debug("Rutas de tipos de extintores registradas")
app.include_router(extinguisher_inspection_routes)
logger.debug("Rutas de inspecciones de extintores registradas")
app.include_router(extinguisher_nested_inspection_routes)
logger.debug("Rutas de inspecciones anidadas de extintores registradas")
app.include_router(extinguisher_inspection_item_routes)
logger.debug("Rutas de ítems de inspección de extintores registradas")
app.include_router(diagnostics_router)


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
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Error no controlado en la API: %s", exc)
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno del servidor."},
    )
