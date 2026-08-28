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

    try:
        yield db
    finally:
        tenant_ids = list(db.info.get("bootstrap_tenant_ids", []))
        db.close()
        transaction.rollback()
        connection.close()

        # Los tenants de prueba se crean mediante bootstrap porque RLS impide
        # crear un tenant desde una sesión normal sin un contexto previo.
        # Una vez finalizada la prueba, se eliminan con la misma conexión
        # privilegiada de bootstrap.
        if tenant_ids:
            cleanup_db = BootstrapSessionLocal()
            try:
                for tenant_id in tenant_ids:
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
