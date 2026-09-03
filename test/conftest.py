import importlib
import os

os.environ["APP_ENV"] = "test"

provision_database_roles = importlib.import_module(
    "scripts.database.environment.02_set_role_passwords"
).main
install_test_database = importlib.import_module(
    "scripts.database.install_users_api_from_zero"
).install_database

# TEST siempre parte de una base limpia y reconstruida hasta Alembic head.
# La contraseña de los roles se configura antes del reset porque el instalador
# conserva los roles y solo reconstruye el schema users_api.
provision_database_roles()
install_test_database(interactive=False)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from UsersAPI.database import BootstrapSessionLocal, engine, get_db
from UsersAPI.main import app
from UsersAPI.security.rate_limiter import rate_limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Aísla el estado del rate limiter entre pruebas."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def db_session():
    """Sesión aislada por prueba; limpia también los datos confirmados por bootstrap."""
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, expire_on_commit=False)

    cleanup_db = BootstrapSessionLocal()
    try:
        existing_tenant_ids = {row[0] for row in cleanup_db.execute(text("SELECT id FROM users_api.tenants")).all()}
    finally:
        cleanup_db.close()

    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()

        cleanup_db = BootstrapSessionLocal()
        try:
            current_created_tenant_ids = {
                row[0]
                for row in cleanup_db.execute(text("SELECT id FROM users_api.tenants")).all()
                if row[0] not in existing_tenant_ids
            }

            if current_created_tenant_ids:
                tenant_ids = tuple(current_created_tenant_ids)
                bind = __import__("sqlalchemy").bindparam

                cleanup_db.execute(text("""
                    DELETE FROM users_api.user_tenant_roles
                    WHERE user_tenant_id IN (
                        SELECT id FROM users_api.user_tenants WHERE tenant_id IN :tenant_ids
                    )
                """).bindparams(bind("tenant_ids", expanding=True)), {"tenant_ids": tenant_ids})

                cleanup_db.execute(text("""
                    DELETE FROM users_api.role_permissions
                    WHERE role_id IN (
                        SELECT id FROM users_api.roles WHERE tenant_id IN :tenant_ids
                    )
                """).bindparams(bind("tenant_ids", expanding=True)), {"tenant_ids": tenant_ids})

                cleanup_db.execute(text("DELETE FROM users_api.roles WHERE tenant_id IN :tenant_ids")
                                   .bindparams(bind("tenant_ids", expanding=True)), {"tenant_ids": tenant_ids})

                candidate_user_ids = {
                    row[0]
                    for row in cleanup_db.execute(text("""
                        SELECT DISTINCT user_id FROM users_api.user_tenants WHERE tenant_id IN :tenant_ids
                    """).bindparams(bind("tenant_ids", expanding=True)), {"tenant_ids": tenant_ids}).all()
                }

                cleanup_db.execute(text("DELETE FROM users_api.user_tenants WHERE tenant_id IN :tenant_ids")
                                   .bindparams(bind("tenant_ids", expanding=True)), {"tenant_ids": tenant_ids})

                if candidate_user_ids:
                    cleanup_db.execute(text("""
                        DELETE FROM users_api.app_users u
                        WHERE u.id IN :user_ids
                          AND NOT EXISTS (
                              SELECT 1 FROM users_api.user_tenants ut WHERE ut.user_id = u.id
                          )
                    """).bindparams(bind("user_ids", expanding=True)), {"user_ids": tuple(candidate_user_ids)})

                cleanup_db.execute(text("DELETE FROM users_api.tenants WHERE id IN :tenant_ids")
                                   .bindparams(bind("tenant_ids", expanding=True)), {"tenant_ids": tenant_ids})

            cleanup_db.commit()
        except Exception:
            cleanup_db.rollback()
            raise
        finally:
            cleanup_db.close()


@pytest.fixture
def client(db_session: Session):
    """Cliente HTTP usando la misma transacción de db_session."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
