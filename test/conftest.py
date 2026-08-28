import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from UsersAPI.database import BootstrapSessionLocal, engine, get_db
from UsersAPI.main import app


@pytest.fixture
def db_session():
    """Sesión aislada por prueba; nunca persiste datos de aplicación."""
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection)

    # /bootstrap utiliza deliberadamente una conexión independiente con
    # users_api_bootstrap (BYPASSRLS), por lo que sus INSERT no participan en
    # la transacción de db_session y no pueden ser revertidos con este rollback.
    # Tomamos un snapshot de tenants existentes para poder limpiar únicamente
    # los tenants creados por el test.
    cleanup_db = BootstrapSessionLocal()
    try:
        existing_tenant_ids = {
            row[0]
            for row in cleanup_db.execute(
                text("SELECT id FROM users_api.tenants")
            ).all()
        }
    finally:
        cleanup_db.close()

    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()

        # Bootstrap confirma en una transacción independiente. Después del
        # rollback de la sesión normal, eliminamos únicamente los tenants que
        # no existían al comenzar el test. Esto evita contaminar la BD real
        # de desarrollo sin deshabilitar RLS en la aplicación.
        cleanup_db = BootstrapSessionLocal()
        try:
            created_tenant_ids = {
                row[0]
                for row in cleanup_db.execute(
                    text("SELECT id FROM users_api.tenants")
                ).all()
                if row[0] not in existing_tenant_ids
            }

            for tenant_id in created_tenant_ids:
                cleanup_db.execute(
                    text("DELETE FROM users_api.tenants WHERE id = :tenant_id"),
                    {"tenant_id": tenant_id},
                )

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
