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
# APLICAR PERMISOS APP
#
# IMPORTANTE:
# Se ejecuta DESPUÉS de Alembic.
#
# En este punto ya existen:
# - tablas
# - secuencias
#
# Por eso ALL TABLES y ALL SEQUENCES sí funcionan.
# ============================================================

def apply_app_permissions(engine):
    print()
    print_separator()
    print("5. APLICAR PERMISOS users_api_app")
    print_separator()

    with engine.begin() as db:

        print("GRANT USAGE ON SCHEMA...")

        db.execute(
            text(
                """
                GRANT USAGE
                ON SCHEMA users_api
                TO users_api_app
                """
            )
        )

        print("GRANT sobre tablas...")

        db.execute(
            text(
                """
                GRANT SELECT, INSERT, UPDATE, DELETE
                ON ALL TABLES IN SCHEMA users_api
                TO users_api_app
                """
            )
        )

        print("GRANT sobre secuencias...")

        db.execute(
            text(
                """
                GRANT USAGE, SELECT
                ON ALL SEQUENCES IN SCHEMA users_api
                TO users_api_app
                """
            )
        )

        print("DEFAULT PRIVILEGES sobre tablas...")

        db.execute(
            text(
                """
                ALTER DEFAULT PRIVILEGES
                FOR ROLE neondb_owner
                IN SCHEMA users_api
                GRANT SELECT, INSERT, UPDATE, DELETE
                ON TABLES
                TO users_api_app
                """
            )
        )

        print("DEFAULT PRIVILEGES sobre secuencias...")

        db.execute(
            text(
                """
                ALTER DEFAULT PRIVILEGES
                FOR ROLE neondb_owner
                IN SCHEMA users_api
                GRANT USAGE, SELECT
                ON SEQUENCES
                TO users_api_app
                """
            )
        )

    print("Permisos users_api_app OK")


# ============================================================
# SEED DE PERMISOS
# ============================================================

def seed_permissions(engine):
    print()
    print_separator()
    print("6. CARGAR PERMISOS")
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
    print("7. CREAR users_api_bootstrap")
    print_separator()

    execute_sql_file(engine, BOOTSTRAP_SQL)


# ============================================================
# VALIDAR PERMISOS APP
# ============================================================

def validate_app_permissions(engine):
    print()
    print_separator()
    print("8. VALIDAR PERMISOS users_api_app")
    print_separator()

    with engine.connect() as db:

        schema_usage = db.execute(
            text(
                """
                SELECT has_schema_privilege(
                    'users_api_app',
                    'users_api',
                    'USAGE'
                )
                """
            )
        ).scalar()

        print(
            f"Schema users_api USAGE: {schema_usage}"
        )

        if not schema_usage:
            raise RuntimeError(
                "users_api_app no tiene USAGE sobre users_api."
            )

        tables_without_insert = db.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'users_api'
                  AND table_type = 'BASE TABLE'
                  AND NOT has_table_privilege(
                      'users_api_app',
                      quote_ident(table_schema) || '.' ||
                      quote_ident(table_name),
                      'INSERT'
                  )
                ORDER BY table_name
                """
            )
        ).fetchall()

        if tables_without_insert:
            print("Tablas sin INSERT:")

            for row in tables_without_insert:
                print(f"  - {row[0]}")

            raise RuntimeError(
                "users_api_app no tiene INSERT sobre todas las tablas."
            )

        sequences_without_usage = db.execute(
            text(
                """
                SELECT sequence_name
                FROM information_schema.sequences
                WHERE sequence_schema = 'users_api'
                  AND NOT has_sequence_privilege(
                      'users_api_app',
                      quote_ident(sequence_schema) || '.' ||
                      quote_ident(sequence_name),
                      'USAGE'
                  )
                ORDER BY sequence_name
                """
            )
        ).fetchall()

        if sequences_without_usage:
            print("Secuencias sin USAGE:")

            for row in sequences_without_usage:
                print(f"  - {row[0]}")

            raise RuntimeError(
                "users_api_app no tiene USAGE sobre todas las secuencias."
            )

        print("Permisos users_api_app OK")


# ============================================================
# VALIDAR PERMISOS BOOTSTRAP
# ============================================================

def validate_bootstrap_permissions(engine):
    print()
    print_separator()
    print("9. VALIDAR PERMISOS users_api_bootstrap")
    print_separator()

    with engine.connect() as db:

        bypass_rls = db.execute(
            text(
                """
                SELECT rolbypassrls
                FROM pg_roles
                WHERE rolname = 'users_api_bootstrap'
                """
            )
        ).scalar()

        print(
            f"users_api_bootstrap BYPASSRLS: {bypass_rls}"
        )

        if not bypass_rls:
            raise RuntimeError(
                "users_api_bootstrap no tiene BYPASSRLS."
            )

        schema_usage = db.execute(
            text(
                """
                SELECT has_schema_privilege(
                    'users_api_bootstrap',
                    'users_api',
                    'USAGE'
                )
                """
            )
        ).scalar()

        print(
            f"Schema users_api USAGE: {schema_usage}"
        )

        if not schema_usage:
            raise RuntimeError(
                "users_api_bootstrap no tiene USAGE sobre users_api."
            )

        sequences_without_usage = db.execute(
            text(
                """
                SELECT sequence_name
                FROM information_schema.sequences
                WHERE sequence_schema = 'users_api'
                  AND NOT has_sequence_privilege(
                      'users_api_bootstrap',
                      quote_ident(sequence_schema) || '.' ||
                      quote_ident(sequence_name),
                      'USAGE'
                  )
                ORDER BY sequence_name
                """
            )
        ).fetchall()

        if sequences_without_usage:
            print("Secuencias sin USAGE:")

            for row in sequences_without_usage:
                print(f"  - {row[0]}")

            raise RuntimeError(
                "users_api_bootstrap no tiene USAGE sobre todas las secuencias."
            )

        print("Permisos users_api_bootstrap OK")


# ============================================================
# VALIDACIÓN GENERAL
# ============================================================

def validate_installation(engine):
    print()
    print_separator()
    print("10. VALIDACIÓN GENERAL")
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

        if len(roles) != 2:
            raise RuntimeError(
                "No se encontraron los dos roles requeridos."
            )

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

        if not tables:
            raise RuntimeError(
                "No se encontraron tablas en users_api."
            )

        # ----------------------------------------------------
        # SECUENCIAS
        # ----------------------------------------------------

        print()
        print("SECUENCIAS users_api:")

        sequences = db.execute(
            text(
                """
                SELECT sequence_name
                FROM information_schema.sequences
                WHERE sequence_schema = 'users_api'
                ORDER BY sequence_name
                """
            )
        ).fetchall()

        for sequence in sequences:
            print(f"  - {sequence[0]}")

        if not sequences:
            print(
                "  - No existen secuencias en users_api."
            )

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

        if not permissions:
            raise RuntimeError(
                "No se encontraron permisos."
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
        settings.database_admin_url,
        pool_pre_ping=True,
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
        # 5. PERMISOS APP
        #
        # IMPORTANTE:
        # Se aplican después de Alembic.
        # ----------------------------------------------------

        apply_app_permissions(engine)

        # ----------------------------------------------------
        # 6. SEED PERMISOS
        # ----------------------------------------------------

        seed_permissions(engine)

        # ----------------------------------------------------
        # 7. BOOTSTRAP ROLE
        # ----------------------------------------------------

        create_bootstrap_role(engine)

        # ----------------------------------------------------
        # 8. VALIDAR APP
        # ----------------------------------------------------

        validate_app_permissions(engine)

        # ----------------------------------------------------
        # 9. VALIDAR BOOTSTRAP
        # ----------------------------------------------------

        validate_bootstrap_permissions(engine)

        # ----------------------------------------------------
        # 10. VALIDACIÓN GENERAL
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