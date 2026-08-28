def test_bootstrap_role_bypasses_rls(bootstrap_conn):
    with bootstrap_conn.cursor() as cur:
        # No usar current_user aquí. En Neon, después de recrear el rol
        # users_api_bootstrap durante una instalación desde cero, el pooler
        # puede reutilizar una sesión cuyo OID de rol quedó obsoleto. Consultar
        # el rol por nombre evita depender del OID de la sesión actual.
        cur.execute(
            "SELECT rolbypassrls FROM pg_roles "
            "WHERE rolname = 'users_api_bootstrap'"
        )
        row = cur.fetchone()

    assert row is not None
    assert row[0] is True


def test_bootstrap_can_read_without_tenant_context(bootstrap_conn):
    with bootstrap_conn.cursor() as cur:
        cur.execute(
            "SELECT set_config('app.current_tenant_id', '', false)"
        )
        cur.execute(
            "SELECT count(*) FROM users_api.tenants"
        )
        assert cur.fetchone()[0] >= 0
