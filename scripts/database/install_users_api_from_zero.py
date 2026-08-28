from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, text

from UsersAPI.settings import settings
from UsersAPI.security.permission_definitions import PERMISSIONS


BASE_DIR = Path(__file__).resolve().parents[2]
APP_SQL = BASE_DIR / "scripts" / "database" / "users_api_app.sql"
BOOTSTRAP_SQL = BASE_DIR / "scripts" / "database" / "users_api_bootstrap.sql"

ROLE_APP = "users_api_app"
ROLE_BOOTSTRAP = "users_api_bootstrap"


def print_separator():
    print("=" * 80)


def execute_sql_file(engine, sql_file: Path):
    print(f"Ejecutando {sql_file.name}...")
    if not sql_file.exists():
        raise FileNotFoundError(f"No existe el archivo: {sql_file}")
    sql = sql_file.read_text(encoding="utf-8")
    with engine.begin() as db:
        db.exec_driver_sql(sql)
    print(f"{sql_file.name} OK")


def terminate_role_sessions(db, role_name: str):
    """Evita sesiones con OID de rol obsoleto en Neon después de DROP ROLE."""
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
        # Primero terminamos las sesiones de los roles que vamos a eliminar.
        # Esto es especialmente importante en Neon: una sesión viva puede
        # conservar un OID de rol que ya no existe y provocar "invalid role OID".
        print(f"Terminando sesiones de {ROLE_APP}...")
        terminate_role_sessions(db, ROLE_APP)

        print(f"Terminando sesiones de {ROLE_BOOTSTRAP}...")
        terminate_role_sessions(db, ROLE_BOOTSTRAP)

        # Los roles pueden ser propietarios del schema u objetos dentro de él.
        # Por eso primero eliminamos los roles con CASCADE y después el schema.
        print(f"Eliminando rol {ROLE_APP}...")
        db.execute(text(f"DROP ROLE IF EXISTS {ROLE_APP} CASCADE"))

        print(f"Eliminando rol {ROLE_BOOTSTRAP}...")
        db.execute(text(f"DROP ROLE IF EXISTS {ROLE_BOOTSTRAP} CASCADE"))

        print("Eliminando esquema users_api...")
        db.execute(text("DROP SCHEMA IF EXISTS users_api CASCADE"))

        print("Eliminando tabla public.alembic_version...")
        db.execute(text("DROP TABLE IF EXISTS public.alembic_version"))

    print("Limpieza completada.")


def create_schema(engine):
    print_separator()
    print("2. CREAR SCHEMA")
    print_separator()
    with engine.begin() as db:
        db.execute(text("CREATE SCHEMA users_api"))
    print("Schema users_api OK")


def create_app_role(engine):
    print_separator()
    print("3. CREAR users_api_app")
    print_separator()
    execute_sql_file(engine, APP_SQL)


def run_alembic():
    print_separator()
    print("4. EJECUTAR ALEMBIC")
    print_separator()
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BASE_DIR,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Alembic upgrade head falló.")
    print("Alembic upgrade head OK")


def apply_app_permissions(engine):
    print_separator()
    print("5. APLICAR PERMISOS users_api_app")
    print_separator()
    with engine.begin() as db:
        db.execute(text("GRANT USAGE ON SCHEMA users_api TO users_api_app"))
        db.execute(
            text(
                "GRANT SELECT, INSERT, UPDATE, DELETE "
                "ON ALL TABLES IN SCHEMA users_api TO users_api_app"
            )
        )
        db.execute(
            text(
                "GRANT USAGE, SELECT "
                "ON ALL SEQUENCES IN SCHEMA users_api TO users_api_app"
            )
        )
        db.execute(
            text(
                "ALTER DEFAULT PRIVILEGES FOR ROLE neondb_owner "
                "IN SCHEMA users_api GRANT SELECT, INSERT, UPDATE, DELETE "
                "ON TABLES TO users_api_app"
            )
        )
        db.execute(
            text(
                "ALTER DEFAULT PRIVILEGES FOR ROLE neondb_owner "
                "IN SCHEMA users_api GRANT USAGE, SELECT "
                "ON SEQUENCES TO users_api_app"
            )
        )
    print("Permisos users_api_app OK")


def seed_permissions(engine):
    print_separator()
    print("6. CARGAR PERMISOS")
    print_separator()
    creados = 0
    existentes = 0

    with engine.begin() as db:
        for code, name, description in PERMISSIONS:
            exists = db.execute(
                text(
                    "SELECT 1 FROM users_api.permissions "
                    "WHERE code = :code LIMIT 1"
                ),
                {"code": code},
            ).fetchone()

            if exists:
                existentes += 1
                continue

            db.execute(
                text(
                    """
                    INSERT INTO users_api.permissions
                        (code, name, description, status, created_by)
                    VALUES
                        (:code, :name, :description, 1, 'SYSTEM')
                    """
                ),
                {
                    "code": code,
                    "name": name,
                    "description": description,
                },
            )
            creados += 1

    print(f"Permisos creados: {creados}")
    print(f"Permisos existentes: {existentes}")
    print("Seed de permisos OK")


def create_bootstrap_role(engine):
    print_separator()
    print("7. CREAR users_api_bootstrap")
    print_separator()
    execute_sql_file(engine, BOOTSTRAP_SQL)


def validate_roles_and_permissions(engine):
    print_separator()
    print("8. VALIDACIÓN DE ROLES Y PERMISOS")
    print_separator()

    with engine.connect() as db:
        roles = db.execute(
            text(
                """
                SELECT rolname, rolcanlogin, rolbypassrls
                FROM pg_roles
                WHERE rolname IN ('users_api_app', 'users_api_bootstrap')
                ORDER BY rolname
                """
            )
        ).fetchall()

        if len(roles) != 2:
            raise RuntimeError("No se encontraron los dos roles requeridos.")

        for role in roles:
            print(role)

        app_schema = db.execute(
            text(
                "SELECT has_schema_privilege('users_api_app', 'users_api', 'USAGE')"
            )
        ).scalar()
        bootstrap_schema = db.execute(
            text(
                "SELECT has_schema_privilege('users_api_bootstrap', 'users_api', 'USAGE')"
            )
        ).scalar()
        bootstrap_bypass = db.execute(
            text(
                "SELECT rolbypassrls FROM pg_roles "
                "WHERE rolname = 'users_api_bootstrap'"
            )
        ).scalar()

        print(f"users_api_app USAGE: {app_schema}")
        print(f"users_api_bootstrap USAGE: {bootstrap_schema}")
        print(f"users_api_bootstrap BYPASSRLS: {bootstrap_bypass}")

        if not app_schema:
            raise RuntimeError("users_api_app no tiene USAGE sobre users_api.")
        if not bootstrap_schema:
            raise RuntimeError(
                "users_api_bootstrap no tiene USAGE sobre users_api."
            )
        if not bootstrap_bypass:
            raise RuntimeError("users_api_bootstrap no tiene BYPASSRLS.")

        permission_count = db.execute(
            text("SELECT count(*) FROM users_api.permissions")
        ).scalar()
        print(f"Total permisos: {permission_count}")

        if permission_count != len(PERMISSIONS):
            raise RuntimeError(
                f"Se esperaban {len(PERMISSIONS)} permisos y existen "
                f"{permission_count}."
            )

        version = db.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).fetchall()
        print("ALEMBIC:")
        for row in version:
            print(f"  - {row[0]}")

    print("Instalación validada correctamente.")


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

    confirmation = input("¿Desea continuar? Escriba SI: ").strip()
    if confirmation != "SI":
        print("Instalación cancelada.")
        return

    engine = create_engine(settings.database_url, pool_pre_ping=True)

    try:
        reset_database(engine)
        create_schema(engine)
        create_app_role(engine)
        run_alembic()
        apply_app_permissions(engine)
        seed_permissions(engine)
        create_bootstrap_role(engine)
        validate_roles_and_permissions(engine)
    finally:
        engine.dispose()

    print_separator()
    print("INSTALACIÓN COMPLETADA CORRECTAMENTE")
    print_separator()


if __name__ == "__main__":
    main()
