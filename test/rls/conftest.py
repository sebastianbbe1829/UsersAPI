import os

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


@pytest.fixture(scope="session")
def bootstrap_conn(bootstrap_database_url):
    with psycopg.connect(bootstrap_database_url) as conn:
        yield conn


@pytest.fixture(scope="session")
def tenant_ids(bootstrap_conn):
    with bootstrap_conn.cursor() as cur:
        cur.execute(
            """
            SELECT id
            FROM users_api.tenants
            WHERE status = 1
            ORDER BY id
            """
        )
        rows = cur.fetchall()

    if len(rows) < 2:
        pytest.skip("Se necesitan al menos dos tenants activos para probar aislamiento RLS")

    return rows[0][0], rows[1][0]


@pytest.fixture
def app_conn(app_database_url):
    with psycopg.connect(app_database_url) as conn:
        yield conn


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
