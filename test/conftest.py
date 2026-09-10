import importlib
import os

os.environ["APP_ENV"] = "test"

install_test_database = importlib.import_module(
    "scripts.database.install_users_api_from_zero"
).install_database

# TEST siempre parte de una base limpia y reconstruida hasta Alembic head.
# Las credenciales se toman de .env.test mediante UsersAPI.settings.
install_test_database(interactive=False)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from UsersAPI.database import BootstrapSessionLocal, engine, get_db  # noqa: E402
from UsersAPI.main import app  # noqa: E402
from UsersAPI.security.rate_limiter import rate_limiter  # noqa: E402


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Aísla el estado del rate limiter entre pruebas."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture(autouse=True)
def mock_cash_context_for_unit_mocks(monkeypatch):
    """Aísla pruebas unitarias de ventas/inventario/cartera del contexto real de Caja.

    Las pruebas que usan una Session real siguen ejecutando la validación real de Caja.
    Los servicios unitarios que usan MagicMock/SimpleNamespace reciben únicamente la
    fecha operativa mínima que necesitan para probar su propia lógica.
    """
    from datetime import date

    from UsersAPI.domains.inventory.services import inventory_movement_service
    from UsersAPI.domains.portfolio.services import portfolio_service
    from UsersAPI.domains.sales.services import sale_service

    real_requirements = {
        sale_service: sale_service.require_operational_context,
        inventory_movement_service: inventory_movement_service.require_operational_context,
        portfolio_service: portfolio_service.require_operational_context,
    }

    def isolated_context(service_module):
        real_requirement = real_requirements[service_module]

        def resolve(db, tenant_id, current_user):
            if isinstance(db, Session):
                return real_requirement(db, tenant_id, current_user)
            return {"business_date": date(2026, 9, 10)}

        return resolve

    monkeypatch.setattr(
        sale_service,
        "require_operational_context",
        isolated_context(sale_service),
    )
    monkeypatch.setattr(
        inventory_movement_service,
        "require_operational_context",
        isolated_context(inventory_movement_service),
    )
    monkeypatch.setattr(
        portfolio_service,
        "require_operational_context",
        isolated_context(portfolio_service),
    )


@pytest.fixture
def db_session():
    """Sesión aislada por prueba; limpia también los datos confirmados por bootstrap."""
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, expire_on_commit=False)

    cleanup_db = BootstrapSessionLocal()
    try:
        existing_tenant_ids = {
            row[0] for row in cleanup_db.execute(text("SELECT id FROM users_api.tenants")).all()
        }
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

                cleanup_db.execute(
                    text("""
                        DELETE FROM users_api.user_tenant_roles
                        WHERE user_tenant_id IN (
                            SELECT id FROM users_api.user_tenants
                            WHERE tenant_id IN :tenant_ids
                        )
                    """).bindparams(bind("tenant_ids", expanding=True)),
                    {"tenant_ids": tenant_ids},
                )

                cleanup_db.execute(
                    text("""
                        DELETE FROM users_api.role_permissions
                        WHERE role_id IN (
                            SELECT id FROM users_api.roles
                            WHERE tenant_id IN :tenant_ids
                        )
                    """).bindparams(bind("tenant_ids", expanding=True)),
                    {"tenant_ids": tenant_ids},
                )

                cleanup_db.execute(
                    text("DELETE FROM users_api.roles WHERE tenant_id IN :tenant_ids").bindparams(
                        bind("tenant_ids", expanding=True)
                    ),
                    {"tenant_ids": tenant_ids},
                )

                candidate_user_ids = {
                    row[0]
                    for row in cleanup_db.execute(
                        text("""
                            SELECT DISTINCT user_id
                            FROM users_api.user_tenants
                            WHERE tenant_id IN :tenant_ids
                        """).bindparams(bind("tenant_ids", expanding=True)),
                        {"tenant_ids": tenant_ids},
                    ).all()
                }

                cleanup_db.execute(
                    text(
                        "DELETE FROM users_api.user_tenants WHERE tenant_id IN :tenant_ids"
                    ).bindparams(bind("tenant_ids", expanding=True)),
                    {"tenant_ids": tenant_ids},
                )

                if candidate_user_ids:
                    cleanup_db.execute(
                        text("""
                            DELETE FROM users_api.app_users u
                            WHERE u.id IN :user_ids
                              AND NOT EXISTS (
                                  SELECT 1
                                  FROM users_api.user_tenants ut
                                  WHERE ut.user_id = u.id
                              )
                        """).bindparams(bind("user_ids", expanding=True)),
                        {"user_ids": tuple(candidate_user_ids)},
                    )

                cleanup_db.execute(
                    text("DELETE FROM users_api.tenants WHERE id IN :tenant_ids").bindparams(
                        bind("tenant_ids", expanding=True)
                    ),
                    {"tenant_ids": tenant_ids},
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
