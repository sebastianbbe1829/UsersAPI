import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.status import (
    HTTP_422_UNPROCESSABLE_CONTENT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from .database import Base, engine
from .routes import user_routes, auth_routers
from .logging_config import logger
from fastapi.middleware.cors import CORSMiddleware


# ============================================================
# APLICACIÓN
# ============================================================

app = FastAPI(
    title="UsersAPI",
    description=(
        "API para gestionar usuarios con búsqueda por DNI, "
        "usando FastAPI y SQLAlchemy."
    ),
    version="1.0.0",
    contact={
        "name": "Sebastian Buitrago Betancur",
        "email": "sebastianbbe@gmail.com",
    },
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
        {
            "name": "Usuarios",
            "description": "Operaciones sobre usuarios",
        },
        {
            "name": "Auth",
            "description": (
                "Autenticación y generación de tokens JWT"
            ),
        },
    ],
)


# ============================================================
# ARCHIVOS ESTÁTICOS
# ============================================================
#
# Estructura:
#
# repo/
# └── UsersAPI/
#     ├── static/
#     │   └── logo.png
#     │
#     └── UsersAPI/
#         └── main.py
#
# Desde main.py:
#
# __file__
#     /.../UsersAPI/UsersAPI/main.py
#
# Un nivel arriba:
#     /.../UsersAPI/UsersAPI
#
# Dos niveles arriba:
#     /.../UsersAPI
#
# Por lo tanto static está en:
#     /.../UsersAPI/static
# ============================================================

CURRENT_FILE = os.path.abspath(__file__)

PACKAGE_DIR = os.path.dirname(CURRENT_FILE)

PROJECT_DIR = os.path.dirname(PACKAGE_DIR)

STATIC_DIR = os.path.join(
    PROJECT_DIR,
    "static",
)

LOGO_PATH = os.path.join(
    STATIC_DIR,
    "logo.png",
)


logger.info("==========================================")
logger.info("CONFIGURACIÓN DE ARCHIVOS ESTÁTICOS")
logger.info("==========================================")

logger.info(
    "CURRENT_FILE: %s",
    CURRENT_FILE,
)

logger.info(
    "PACKAGE_DIR: %s",
    PACKAGE_DIR,
)

logger.info(
    "PROJECT_DIR: %s",
    PROJECT_DIR,
)

logger.info(
    "STATIC_DIR: %s",
    STATIC_DIR,
)

logger.info(
    "LOGO_PATH: %s",
    LOGO_PATH,
)

logger.info(
    "STATIC_EXISTS: %s",
    os.path.exists(STATIC_DIR),
)

logger.info(
    "LOGO_EXISTS: %s",
    os.path.exists(LOGO_PATH),
)

logger.info("==========================================")


if os.path.isdir(STATIC_DIR):

    app.mount(
        "/static",
        StaticFiles(
            directory=STATIC_DIR,
        ),
        name="static",
    )

    logger.info(
        "Directorio /static montado correctamente"
    )

else:

    logger.error(
        "NO SE ENCONTRÓ EL DIRECTORIO STATIC: %s",
        STATIC_DIR,
    )


# ============================================================
# CORS
# ============================================================

origins = [
    "http://localhost:5173",
    "https://gestion-usuarios.sebastianbbe.workers.dev",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# INICIO DE LA APLICACIÓN
# ============================================================

logger.info(
    "Iniciando aplicación UsersAPI"
)


# ============================================================
# BASE DE DATOS
# ============================================================

logger.debug(
    "URL BD: %s",
    engine.url,
)

Base.metadata.create_all(
    bind=engine
)

logger.info(
    "Tablas de base de datos creadas y esquema verificado"
)


# ============================================================
# RUTAS DE USUARIOS
# ============================================================

app.include_router(
    user_routes
)

logger.info(
    "Rutas de usuarios registradas"
)


# ============================================================
# RUTAS DE AUTENTICACIÓN
# ============================================================

app.include_router(
    auth_routers
)

logger.info(
    "Rutas de autenticación registradas"
)


# ============================================================
# MANEJO DE ERRORES DE VALIDACIÓN
# ============================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):

    logger.warning(
        "Error de validación en %s: %s",
        request.url.path,
        exc,
    )

    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": exc.errors(),
        },
    )


# ============================================================
# MANEJO DE ERRORES GENERALES
# ============================================================

@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
):

    logger.exception(
        "Error no controlado en %s",
        request.url.path,
    )

    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Error interno del servidor",
        },
    )