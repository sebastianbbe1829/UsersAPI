import asyncio
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT, HTTP_500_INTERNAL_SERVER_ERROR

from .database import engine
from .routes import (
    user_routes, auth_routers, global_auth_routes, tenant_routes, tenant_config_routes,
    tenant_config_public_routes, user_tenant_routes, role_routes, user_tenant_role_routes,
    role_permission_routes, bootstrap_tenant_routes, permission_routes, email_routes,
    otp_routes, extinguisher_routes, extinguisher_type_routes, extinguisher_inspection_routes,
    extinguisher_nested_inspection_routes, extinguisher_inspection_item_routes,
)
from .logging_config import logger
from .services.extinguisher_recharge_job import daily_extinguisher_recharge_job
from fastapi.middleware.cors import CORSMiddleware

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
    swagger_ui_parameters={"docExpansion": "none", "displayRequestDuration": True, "defaultModelsExpandDepth": 0,
                           "defaultModelExpandDepth": 1, "filter": True, "syntaxHighlight": True,
                           "persistAuthorization": True, "tryItOutEnabled": True, "deepLinking": True},
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
        {"name": "OTP", "description": "Generación y validación de códigos OTP temporales"},
        {"name": "Extintores", "description": "Inventario y gestión de extintores por tenant"},
        {"name": "Tipos de extintor", "description": "Catálogo global de tipos de extintor"},
        {"name": "Revisiones de extintores", "description": "Histórico y control de revisiones de extintores"},
        {"name": "Ítems de revisión", "description": "Catálogo de ítems utilizados en las revisiones de extintores"},
    ],
)

origins = ["http://localhost:5173", "https://gestion-usuarios.sebastianbbe.workers.dev"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_daily_job_stop_event: asyncio.Event | None = None
_daily_job_task: asyncio.Task | None = None


@app.on_event("startup")
async def start_daily_extinguisher_recharge_job():
    global _daily_job_stop_event, _daily_job_task
    _daily_job_stop_event = asyncio.Event()
    _daily_job_task = asyncio.create_task(daily_extinguisher_recharge_job(_daily_job_stop_event))
    logger.info("Daily extinguisher recharge notification worker started")


@app.on_event("shutdown")
async def stop_daily_extinguisher_recharge_job():
    global _daily_job_stop_event, _daily_job_task
    if _daily_job_stop_event:
        _daily_job_stop_event.set()
    if _daily_job_task:
        try:
            await asyncio.wait_for(_daily_job_task, timeout=5)
        except asyncio.TimeoutError:
            _daily_job_task.cancel()
            try:
                await _daily_job_task
            except asyncio.CancelledError:
                pass
    _daily_job_stop_event = None
    _daily_job_task = None
    logger.info("Daily extinguisher recharge notification worker stopped")


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
app.include_router(otp_routes)
app.include_router(extinguisher_routes)
app.include_router(extinguisher_type_routes)
app.include_router(extinguisher_inspection_routes)
app.include_router(extinguisher_nested_inspection_routes)
app.include_router(extinguisher_inspection_item_routes)


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
