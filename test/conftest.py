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
    db = Session(bind=connection, expire_on_commit=False)

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
        # Guardamos los tenants creados por este test antes de cerrar la
        # sesión, ya que create_user_context() los registra en db.info.
        created_tenant_ids = set(db.info.get("bootstrap_tenant_ids", []))

        db.close()
        transaction.rollback()
        connection.close()

        # Bootstrap confirma en una transacción independiente. Después del
        # rollback de la sesión normal, eliminamos únicamente los tenants que
        # no existían al comenzar el test y los usuarios globales de app_users
        # que quedaron asociados exclusivamente a esos tenants.
        cleanup_db = BootstrapSessionLocal()
        try:
            current_created_tenant_ids = {
                row[0]
                for row in cleanup_db.execute(
                    text("SELECT id FROM users_api.tenants")
                ).all()
                if row[0] not in existing_tenant_ids
            }

            if created_tenant_ids:
                current_created_tenant_ids &= created_tenant_ids

            if current_created_tenant_ids:
                tenant_ids = tuple(current_created_tenant_ids)

                # Primero eliminamos las filas dependientes de los tenants.
                # app_users no puede eliminarse mientras existan user_tenants
                # que lo referencien.
                cleanup_db.execute(
                    text(
                        """
                        DELETE FROM users_api.user_tenant_roles
                        WHERE user_tenant_id IN (
                            SELECT id
                            FROM users_api.user_tenants
                            WHERE tenant_id IN :tenant_ids
                        )
                        """
                    ).bindparams(
                        __import__("sqlalchemy").bindparam(
                            "tenant_ids", expanding=True
                        )
                    ),
                    {"tenant_ids": tenant_ids},
                )

                cleanup_db.execute(
                    text(
                        """
                        DELETE FROM users_api.role_permissions
                        WHERE role_id IN (
                            SELECT id
                            FROM users_api.roles
                            WHERE tenant_id IN :tenant_ids
                        )
                        """
                    ).bindparams(
                        __import__("sqlalchemy").bindparam(
                            "tenant_ids", expanding=True
                        )
                    ),
                    {"tenant_ids": tenant_ids},
                )

                cleanup_db.execute(
                    text(
                        """
                        DELETE FROM users_api.roles
                        WHERE tenant_id IN :tenant_ids
                        """
                    ).bindparams(
                        __import__("sqlalchemy").bindparam(
                            "tenant_ids", expanding=True
                        )
                    ),
                    {"tenant_ids": tenant_ids},
                )

                # Guardamos los usuarios que quedarán libres después de
                # eliminar sus asociaciones con estos tenants.
                candidate_user_ids = {
                    row[0]
                    for row in cleanup_db.execute(
                        text(
                            """
                            SELECT DISTINCT user_id
                            FROM users_api.user_tenants
                            WHERE tenant_id IN :tenant_ids
                            """
                        ).bindparams(
                            __import__("sqlalchemy").bindparam(
                                "tenant_ids", expanding=True
                            )
                        ),
                        {"tenant_ids": tenant_ids},
                    ).all()
                }

                cleanup_db.execute(
                    text(
                        """
                        DELETE FROM users_api.user_tenants
                        WHERE tenant_id IN :tenant_ids
                        """
                    ).bindparams(
                        __import__("sqlalchemy").bindparam(
                            "tenant_ids", expanding=True
                        )
                    ),
                    {"tenant_ids": tenant_ids},
                )

                if candidate_user_ids:
                    cleanup_db.execute(
                        text(
                            """
                            DELETE FROM users_api.app_users u
                            WHERE u.id IN :user_ids
                              AND NOT EXISTS (
                                  SELECT 1
                                  FROM users_api.user_tenants ut
                                  WHERE ut.user_id = u.id
                              )
                            """
                        ).bindparams(
                            __import__("sqlalchemy").bindparam(
                                "user_ids", expanding=True
                            )
                        ),
                        {"user_ids": tuple(candidate_user_ids)},
                    )

                cleanup_db.execute(
                    text(
                        "DELETE FROM users_api.tenants WHERE id IN :tenant_ids"
                    ).bindparams(
                        __import__("sqlalchemy").bindparam(
                            "tenant_ids", expanding=True
                        )
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
