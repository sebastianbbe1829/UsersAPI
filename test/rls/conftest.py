import os
from uuid import uuid4

import pytest
import psycopg


@pytest.fixture(scope="session")
def app_database_url():
    url = os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL no está configurada")
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


@pytest.fixture(scope="session")
def bootstrap_database_url():
    url = os.getenv("BOOTSTRAP_DATABASE_URL")
    if not url:
        pytest.skip("BOOTSTRAP_DATABASE_URL no está configurada")
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


@pytest.fixture
def bootstrap_conn(bootstrap_database_url):
    with psycopg.connect(bootstrap_database_url) as conn:
        try:
            yield conn
        finally:
            conn.rollback()


@pytest.fixture
def tenant_ids(bootstrap_database_url):
    """Crea dos tenants y un usuario temporales para las pruebas RLS."""
    suffix = uuid4().hex[:12]
    tenant_ids = []
    user_id = None

    with psycopg.connect(bootstrap_database_url) as conn:
        try:
            with conn.cursor() as cur:
                for label in ("A", "B"):
                    cur.execute(
                        """
                        INSERT INTO users_api.tenants
                            (name, slug, status, created_at, created_by)
                        VALUES
                            (%s, %s, 1, now(), 'pytest')
                        RETURNING id
                        """,
                        (
                            f"RLS Test Tenant {label} {suffix}",
                            f"rls-test-{label.lower()}-{suffix}",
                        ),
                    )
                    tenant_ids.append(cur.fetchone()[0])

                cur.execute(
                    """
                    INSERT INTO users_api.app_users
                        (dni, name, created_at, created_by)
                    VALUES
                        (%s, 'RLS Test User', now(), 'pytest')
                    RETURNING id
                    """,
                    (f"9{uuid4().int % 10000000:07d}",),
                )
                user_id = cur.fetchone()[0]

            conn.commit()
            yield tuple(tenant_ids)
        finally:
            with conn.cursor() as cur:
                if tenant_ids:
                    cur.execute(
                        """
                        DELETE FROM users_api.user_tenants
                        WHERE tenant_id = ANY(%s)
                        """,
                        (tenant_ids,),
                    )

                    cur.execute(
                        """
                        DELETE FROM users_api.tenants
                        WHERE id = ANY(%s)
                        """,
                        (tenant_ids,),
                    )

                if user_id is not None:
                    cur.execute(
                        "DELETE FROM users_api.app_users WHERE id = %s",
                        (user_id,),
                    )
            conn.commit()


def set_tenant(conn, tenant_id):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT set_config('app.current_tenant_id', %s, false)",
            (str(tenant_id),),
        )


def clear_tenant(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT set_config('app.current_tenant_id', '', false)"
        )
