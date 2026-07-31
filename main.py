from fastapi import FastAPI
from .database import Base, engine
from .routes import user_routes
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
    },
    openapi_tags=[
        {"name": "Usuarios", "description": "Operaciones sobre usuarios"},
    ],
)

logger.info("Iniciando aplicación UsersAPI")

# Crear tablas
Base.metadata.create_all(bind=engine)
logger.info("Tablas de base de datos creadas y esquema verificado")

# Incluir rutas
app.include_router(user_routes)
logger.info("Rutas registradas")
