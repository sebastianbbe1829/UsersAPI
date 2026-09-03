"""Provision PostgreSQL application roles for the selected environment.

The database admin connection is selected through APP_ENV by UsersAPI.settings.
Passwords are read only from the process environment and are never stored in Git.
"""

import os
import sys

from psycopg import sql
from sqlalchemy import create_engine

from UsersAPI.settings import settings

APP_ROLE = "users_api_app"
BOOTSTRAP_ROLE = "users_api_bootstrap"
APP_PASSWORD_ENV = "USERS_API_APP_PASSWORD"
BOOTSTRAP_PASSWORD_ENV = "USERS_API_BOOTSTRAP_PASSWORD"


def _ensure_role(cursor, role_name: str, *, bypass_rls: bool) -> None:
    cursor.execute(
        "SELECT 1 FROM pg_roles WHERE rolname = %s",
        (role_name,),
    )
    if cursor.fetchone() is None:
        cursor.execute(
            sql.SQL(
                "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                "NOINHERIT NOBYPASSRLS"
            ).format(sql.Identifier(role_name))
        )

    if bypass_rls:
        cursor.execute(
            sql.SQL("ALTER ROLE {} INHERIT BYPASSRLS").format(
                sql.Identifier(role_name)
            )
        )
    else:
        cursor.execute(
            sql.SQL("ALTER ROLE {} NOINHERIT NOBYPASSRLS").format(
                sql.Identifier(role_name)
            )
        )


def main() -> int:
    if not settings.database_admin_url:
        raise RuntimeError("DATABASE_ADMIN_URL no está configurada.")

    app_password = os.getenv(APP_PASSWORD_ENV)
    bootstrap_password = os.getenv(BOOTSTRAP_PASSWORD_ENV)

    if not app_password or not bootstrap_password:
        missing = [
            name
            for name, value in (
                (APP_PASSWORD_ENV, app_password),
                (BOOTSTRAP_PASSWORD_ENV, bootstrap_password),
            )
            if not value
        ]
        raise RuntimeError(
            "Faltan variables de contraseña: " + ", ".join(missing)
        )

    engine = create_engine(settings.database_admin_url, pool_pre_ping=True)
    raw_connection = engine.raw_connection()

    try:
        with raw_connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA IF NOT EXISTS users_api")

            _ensure_role(cursor, APP_ROLE, bypass_rls=False)
            _ensure_role(cursor, BOOTSTRAP_ROLE, bypass_rls=True)

            cursor.execute(
                sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(APP_ROLE),
                    sql.Literal(app_password),
                )
            )
            cursor.execute(
                sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(BOOTSTRAP_ROLE),
                    sql.Literal(bootstrap_password),
                )
            )

            cursor.execute(
                sql.SQL("GRANT USAGE ON SCHEMA users_api TO {}").format(
                    sql.Identifier(APP_ROLE)
                )
            )
            cursor.execute(
                sql.SQL("GRANT USAGE ON SCHEMA users_api TO {}").format(
                    sql.Identifier(BOOTSTRAP_ROLE)
                )
            )

        raw_connection.commit()
    except Exception:
        raw_connection.rollback()
        raise
    finally:
        raw_connection.close()
        engine.dispose()

    print("Roles de base de datos configurados correctamente.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
