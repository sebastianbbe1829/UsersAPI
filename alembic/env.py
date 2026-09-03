from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy import engine_from_config
from sqlalchemy import Identity

from alembic import context

from UsersAPI.database import Base
import UsersAPI.models  # noqa: F401
from UsersAPI.settings import settings


# ============================================================
# CONFIGURACIÓN ALEMBIC
# ============================================================

config = context.config

# La URL de base de datos nunca se almacena en alembic.ini.
# Se obtiene desde la configuración central de la aplicación.
if not settings.database_admin_url:
    raise RuntimeError(
        "DATABASE_ADMIN_URL no está configurada"
    )

config.set_main_option(
    "sqlalchemy.url",
    settings.database_admin_url,
)


# ============================================================
# LOGGING
# ============================================================

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ============================================================
# METADATA SQLALCHEMY
# ============================================================

target_metadata = Base.metadata


# ============================================================
# ESQUEMA ADMINISTRADO
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
    Alembic solamente administra users_api
    """

    if type_ == "schema":
        return name == DB_SCHEMA

    if type_ == "table":
        schema = parent_names.get("schema_name")
        return schema == DB_SCHEMA

    return True


def compare_server_default(
    context_,
    inspected_column,
    metadata_column,
    inspected_default,
    metadata_default,
    rendered_metadata_default,
):
    """
    Treat PostgreSQL SERIAL and SQLAlchemy Identity as equivalent
    auto-increment strategies for existing integer primary keys.

    The project contains legacy migrations that create SERIAL-backed
    primary keys while current models use Identity. Both provide the
    same application-level auto-increment behavior, so alembic check
    should not require a data migration solely to change that mechanism.
    """

    if isinstance(metadata_column.identity, Identity):
        return False

    return None


# ============================================================
# OFFLINE
# ============================================================

def run_migrations_offline() -> None:

    url = config.get_main_option(
        "sqlalchemy.url"
    )

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named"
        },
        include_schemas=True,
        include_name=include_name,
        compare_server_default=compare_server_default,
    )

    with context.begin_transaction():

        context.run_migrations()


# ============================================================
# ONLINE
# ============================================================

def run_migrations_online() -> None:

    configuration = config.get_section(
        config.config_ini_section
    )

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_name=include_name,
            compare_server_default=compare_server_default,
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
