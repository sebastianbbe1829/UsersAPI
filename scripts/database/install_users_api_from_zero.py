from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, text

from UsersAPI.settings import settings
from UsersAPI.security.permission_definitions import PERMISSIONS


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

APP_SQL = BASE_DIR / "scripts" / "database" / "users_api_app.sql"
BOOTSTRAP_SQL = BASE_DIR / "scripts" / "database" / "users_api_bootstrap.sql"

SCHEMA_NAME = "users_api"

ROLE_APP = "users_api_app"
ROLE_BOOTSTRAP = "users_api_bootstrap"


# ============================================================
# UTILIDADES
# ============================================================

def print_separator():
    print("=" * 80)


def execute_sql_file(engine, sql_file: Path):
    print(f"Ejecutando {sql_file.name}...")

    if not sql_file.exists():
        raise FileNotFoundError(
            f"No existe el archivo: {sql_file}"
        )

    sql = sql_file.read_text(encoding="utf-8")

    with engine.begin() as db:
        db.exec_driver_sql(sql)

    print(f"{sql_file.name} OK")


# ============================================================
# RESET
# ============================================================

def terminate_role_sessions(db, role_name: str):
    """Termina sesiones activas antes de eliminar y recrear un rol."""

    db.execute(
        text(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE usename = :role_name
              AND pid <> pg_backend_pid()
            """
        ),
        {"role_name": role_name},
    )


def reset_database(engine):
    print_separator()
    print("1. RESET")
    print_separator()

    with engine.begin() as db:

        print("Eliminando esquema users_api...")

        db.execute(
            text(
                """
                DROP SCHEMA IF EXISTS users_api CASCADE
                """
            )
        )

        print("Eliminando tabla public.alembic_version...")

        db.execute(
            text(
                """
                DROP TABLE IF EXISTS public.alembic_version
                """
            )
        )

        print("Terminando sesiones de users_api_app...")
        terminate_role_sessions(db, ROLE_APP)

        print("Terminando sesiones de users_api_bootstrap...")
        terminate_role_sessions(db, ROLE_BOOTSTRAP)

        print("Eliminando rol users_api_app...")

        db.execute(
            text(
                f"""
                DROP ROLE IF EXISTS {ROLE_APP}
                """
            )
        )

        print("Eliminando rol users_api_bootstrap...")

        db.execute(
            text(
                f"""
                DROP ROLE IF EXISTS {ROLE_BOOTSTRAP}
                """
            )
        )

    print("Limpieza completada.")


# ============================================================
# CREAR SCHEMA
# ============================================================

def create_schema(engine):
    print()
    print_separator()
    print("2. CREAR SCHEMA")
    print_separator()

    print()
    print("Creando schema users_api...")

    with engine.begin() as db:
        db.execute(
            text(
                """
                CREATE SCHEMA users_api
                """
            )
        )

    print("Schema users_api OK")


# ============================================================
# CREAR users_api_app
# ============================================================

def create_app_role(engine):
    print()
    print_separator()
    print("3. CREAR users_api_app")
    print_separator()

    execute_sql_file(engine, APP_SQL)


# ============================================================
# EJECUTAR ALEMBIC
# ============================================================

def run_alembic():
    print()
    print_separator()
    print("4. EJECUTAR ALEMBIC")
    print_separator()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "upgrade",
            "head",
        ],
        cwd=BASE_DIR,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Alembic upgrade head falló."
        )

    print()
    print("Alembic upgrade head OK")


# ============================================================
# APLICAR PERMISOS APP
#
# IMPORTANTE:
# Se ejecuta DESPUÉS de Alembic.
#
# En este punto ya existen:
# - tablas
