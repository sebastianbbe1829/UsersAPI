def test_resolver_returns_tenant_for_pending_association(bootstrap_conn):
    with bootstrap_conn.cursor() as cur:
        cur.execute(
            """
            SELECT activation_token
            FROM users_api.user_tenants
            WHERE status = 0
              AND activation_token IS NOT NULL
            ORDER BY id
            LIMIT 1
            """
        )
        row = cur.fetchone()

    if row is None:
        return

    with bootstrap_conn.cursor() as cur:
        cur.execute(
            "SELECT users_api.resolve_tenant_id_by_activation_token(%s)",
            (row[0],),
        )
        tenant_id = cur.fetchone()[0]

    assert tenant_id is not None


def test_app_role_can_use_resolver_before_setting_context(app_conn, bootstrap_conn):
    with bootstrap_conn.cursor() as cur:
        cur.execute(
            """
            SELECT activation_token
            FROM users_api.user_tenants
            WHERE status = 0
              AND activation_token IS NOT NULL
            ORDER BY id
            LIMIT 1
            """
        )
        row = cur.fetchone()

    if row is None:
        return

    with app_conn.cursor() as cur:
        cur.execute(
            "SELECT users_api.resolve_tenant_id_by_activation_token(%s)",
            (row[0],),
        )
        tenant_id = cur.fetchone()[0]
        assert tenant_id is not None

        cur.execute(
            "SELECT set_config('app.current_tenant_id', %s, false)",
            (str(tenant_id),),
        )

        cur.execute(
            """
            SELECT count(*)
            FROM users_api.user_tenants
            WHERE activation_token = %s
              AND tenant_id = %s
            """,
            (row[0], tenant_id),
        )
        assert cur.fetchone()[0] == 1
