def test_bootstrap_role_bypasses_rls(bootstrap_conn):
    with bootstrap_conn.cursor() as cur:
        cur.execute(
            "SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user"
        )
        assert cur.fetchone()[0] is True


def test_bootstrap_can_read_without_tenant_context(bootstrap_conn):
    with bootstrap_conn.cursor() as cur:
        cur.execute(
            "SELECT set_config('app.current_tenant_id', '', false)"
        )
        cur.execute(
            "SELECT count(*) FROM users_api.tenants"
        )
        assert cur.fetchone()[0] >= 1
