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
# SEED DE PERMISOS
# ============================================================

def seed_permissions(engine):
    print()
    print_separator()
    print("5. CARGAR PERMISOS")
    print_separator()

    print()
    print("Cargando permisos mediante conexión administrativa...")

    creados = 0
    existentes = 0

    with engine.begin() as db:

        for code, name, description in PERMISSIONS:

            permission = db.execute(
                text(
                    """
                    SELECT id
                    FROM users_api.permissions
                    WHERE code = :code
                    LIMIT 1
                    """
                ),
                {
                    "code": code,
                },
            ).fetchone()

            if permission:
                existentes += 1
                continue

            db.execute(
                text(
                    """
                    INSERT INTO users_api.permissions (
                        code,
                        name,
                        description,
                        status,
                        created_by
                    )
                    VALUES (
                        :code,
                        :name,
                        :description,
                        1,
                        'SYSTEM'
                    )
                    """
                ),
                {
                    "code": code,
                    "name": name,
                    "description": description,
                },
            )

            creados += 1

    print()
    print(f"Permisos creados: {creados}")
    print(f"Permisos existentes: {existentes}")
    print()
    print("Seed de permisos OK")


# ============================================================
# CREAR users_api_bootstrap
# ============================================================

def create_bootstrap_role(engine):
    print()
    print_separator()
    print("6. CREAR users_api_bootstrap")
    print_separator()

    execute_sql_file(engine, BOOTSTRAP_SQL)


# ============================================================
# VALIDACIÓN
# ============================================================

def validate_installation(engine):
    print()
    print_separator()
    print("7. VALIDACIÓN")
    print_separator()

    print()
    print_separator()
    print("VALIDANDO INSTALACIÓN")
    print_separator()

    with engine.connect() as db:

        # ----------------------------------------------------
        # ROLES
        # ----------------------------------------------------

        print()
        print("ROLES:")

        roles = db.execute(
            text(
                """
                SELECT
                    rolname,
                    rolcanlogin,
                    rolbypassrls
                FROM pg_roles
                WHERE rolname IN (
                    'users_api_app',
                    'users_api_bootstrap'
                )
                ORDER BY rolname
                """
            )
        ).fetchall()

        for role in roles:
            print(role)

        # ----------------------------------------------------
        # TABLAS
        # ----------------------------------------------------

        print()
        print("TABLAS users_api:")

        tables = db.execute(
            text(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'users_api'
                ORDER BY tablename
                """
            )
        ).fetchall()

        for table in tables:
            print(f"  - {table[0]}")

        # ----------------------------------------------------
        # PERMISOS
        # ----------------------------------------------------

        print()
        print("PERMISOS:")

        permissions = db.execute(
            text(
                """
                SELECT
                    code,
                    name,
                    status
                FROM users_api.permissions
                ORDER BY id
                """
            )
        ).fetchall()

        for permission in permissions:
            print(
                f"  - {permission[0]} | "
                f"{permission[1]} | "
                f"status={permission[2]}"
            )

        print()
        print(
            f"Total permisos: {len(permissions)}"
        )

        # ----------------------------------------------------
        # ALEMBIC
        # ----------------------------------------------------

        print()
        print("ALEMBIC:")

        alembic_exists = db.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name = 'alembic_version'
                )
                """
            )
        ).scalar()

        if alembic_exists:

            versions = db.execute(
                text(
                    """
                    SELECT version_num
                    FROM public.alembic_version
                    ORDER BY version_num
                    """
                )
            ).fetchall()

            for version in versions:
                print(f"  - {version[0]}")

        else:
            print("  - NO EXISTE")

        # ----------------------------------------------------
        # VALIDACIONES BÁSICAS
        # ----------------------------------------------------

        print()

        if not roles:
            raise RuntimeError(
                "No se encontraron los roles requeridos."
            )

        if not tables:
            raise RuntimeError(
                "No se encontraron tablas en users_api."
            )

        if not permissions:
            raise RuntimeError(
                "No se encontraron permisos."
            )

        if not alembic_exists:
            raise RuntimeError(
                "No existe public.alembic_version."
            )

    print()
    print("Instalación validada correctamente.")


# ============================================================
# MAIN
# ============================================================

def main():

    print_separator()
    print("USERS API - INSTALACIÓN DESDE CERO")
    print_separator()

    print()
    print("ADVERTENCIA:")
    print("Este proceso ELIMINA completamente el esquema users_api")
    print("y elimina los roles users_api_app y users_api_bootstrap.")
    print("Se reconstruirá toda la estructura desde cero.")
    print()

    confirmacion = input(
        "¿Desea continuar? Escriba SI: "
    ).strip().upper()

    if confirmacion != "SI":
        print()
        print("Instalación cancelada.")
        return

    print()

    # --------------------------------------------------------
    # ENGINE ADMIN
    # --------------------------------------------------------

    engine = create_engine(
        settings.database_admin_url
    )

    try:

        # ----------------------------------------------------
        # 1. RESET
        # ----------------------------------------------------

        reset_database(engine)

        # ----------------------------------------------------
        # 2. SCHEMA
        # ----------------------------------------------------

        create_schema(engine)

        # ----------------------------------------------------
        # 3. APP ROLE
        # ----------------------------------------------------

        create_app_role(engine)

        # ----------------------------------------------------
        # 4. ALEMBIC
        # ----------------------------------------------------

        run_alembic()

        # ----------------------------------------------------
        # 5. PERMISOS
        # ----------------------------------------------------

        seed_permissions(engine)

        # ----------------------------------------------------
        # 6. BOOTSTRAP ROLE
        # ----------------------------------------------------

        create_bootstrap_role(engine)

        # ----------------------------------------------------
        # 7. VALIDACIÓN
        # ----------------------------------------------------

        validate_installation(engine)

    finally:

        engine.dispose()

    print()
    print_separator()
    print("INSTALACIÓN COMPLETADA CORRECTAMENTE")
    print_separator()


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    main()