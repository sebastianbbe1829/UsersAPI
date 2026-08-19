from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from UsersAPI.database import Base, engine
from UsersAPI.models.user import UserDB


# ============================================================
# CONFIGURACIÓN ALEMBIC
# ============================================================

config = context.config


# ============================================================
# LOGGING
# ============================================================

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ============================================================
# METADATA DE SQLALCHEMY
# ============================================================

target_metadata = Base.metadata


# ============================================================
# ESQUEMA QUE ADMINISTRA ESTA APLICACIÓN
# ============================================================

DB_SCHEMA = "users_api"


# ============================================================
# FILTRO DE OBJETOS
# ============================================================

def include_name(
    name,
    type_,
    parent_names,
):
    """
    Indica qué objetos debe considerar Alembic.

    La aplicación solamente administra
    el esquema users_api.
    """

    if type_ == "schema":
        return name == DB_SCHEMA

    if type_ == "table":
        schema = parent_names.get("schema_name")
        return schema == DB_SCHEMA

    return True


# ============================================================
# MIGRACIÓN OFFLINE
# ============================================================

def run_migrations_offline() -> None:

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named"
        },
        include_schemas=True,
        include_name=include_name,
    )

    with context.begin_transaction():

        context.run_migrations()


# ============================================================
# MIGRACIÓN ONLINE
# ============================================================

def run_migrations_online() -> None:

    connectable = engine

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_name=include_name,
        )

        with context.begin_transaction():

            context.run_migrations()


# ============================================================
# EJECUCIÓN
# ============================================================

if context.is_offline_mode():

    run_migrations_offline()

else:

    run_migrations_online()