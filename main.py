from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT, HTTP_500_INTERNAL_SERVER_ERROR

from .database import Base, engine
from .routes import user_routes, auth_routers
from .logging_config import logger

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
        {"name": "Auth", "description": "Autenticación y generación de tokens JWT"},
    ],
)

logger.info("Iniciando aplicación UsersAPI")

# Crear tablas
logger.debug("URL BD: %s", engine.url)
Base.metadata.create_all(bind=engine)
logger.info("Tablas de base de datos creadas y esquema verificado")

# Incluir rutas
app.include_router(user_routes)
logger.info("Rutas de usuarios registradas")

app.include_router(auth_routers)
logger.info("Rutas de autenticación registradas")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Error de validación en %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Error no controlado en %s", request.url.path)
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno del servidor"},
    )

