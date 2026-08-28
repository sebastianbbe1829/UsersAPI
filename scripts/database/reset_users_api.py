from UsersAPI.settings import settings
from sqlalchemy import create_engine, text


engine = create_engine(settings.database_admin_url)


with engine.begin() as db:

    print("Eliminando esquema users_api...")

    db.execute(
        text("DROP SCHEMA IF EXISTS users_api CASCADE")
    )

    print("Eliminando tabla public.alembic_version...")

    db.execute(
        text("DROP TABLE IF EXISTS public.alembic_version")
    )

    print("Eliminando rol users_api_app...")

    db.execute(
        text("DROP ROLE IF EXISTS users_api_app")
    )

    print("Eliminando rol users_api_bootstrap...")

    db.execute(
        text("DROP ROLE IF EXISTS users_api_bootstrap")
    )

    print("Limpieza completada.")


engine.dispose()