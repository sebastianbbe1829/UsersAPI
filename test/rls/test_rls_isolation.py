import psycopg


def set_tenant(conn, tenant_id):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT set_config('app.current_tenant_id', %s, false)",
            (str(tenant_id),),
        )


def test_app_role_has_rls_enabled_on_user_tenants(app_conn):
    with app_conn.cursor() as cur:
        cur.execute(
            """
            SELECT relrowsecurity, relforcerowsecurity
            FROM pg_class
            WHERE oid = 'users_api.user_tenants'::regclass
            """
        )
        enabled, forced = cur.fetchone()

    assert enabled is True
    assert forced is True


def test_app_role_does_not_bypass_rls(app_conn):
    with app_conn.cursor() as cur:
        cur.execute(
            "SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user"
        )
        assert cur.fetchone()[0] is False


def test_tenant_isolation_on_user_tenants(app_conn, tenant_ids):
    tenant_a, tenant_b = tenant_ids
    set_tenant(app_conn, tenant_a)

    with app_conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM users_api.user_tenants WHERE tenant_id = %s",
            (tenant_a,),
        )
        visible_a = cur.fetchone()[0]

        cur.execute(
            "SELECT count(*) FROM users_api.user_tenants WHERE tenant_id = %s",
            (tenant_b,),
        )
        visible_b = cur.fetchone()[0]

    assert visible_a >= 0
    assert visible_b == 0


def test_cross_tenant_insert_is_blocked(app_conn, bootstrap_conn, tenant_ids):
    tenant_a, tenant_b = tenant_ids

    with bootstrap_conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM users_api.users ORDER BY id LIMIT 1"
        )
        user_id = cur.fetchone()[0]

    set_tenant(app_conn, tenant_a)

    try:
        with app_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users_api.user_tenants (user_id, tenant_id, status)
                VALUES (%s, %s, 0)
                """,
                (user_id, tenant_b),
            )
    except psycopg.errors.InsufficientPrivilege as exc:
        assert exc.sqlstate == "42501"
        app_conn.rollback()
        return

    app_conn.rollback()
    raise AssertionError("RLS permitió insertar una asociación para otro tenant")
