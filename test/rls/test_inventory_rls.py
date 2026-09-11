import psycopg


def set_tenant(conn, tenant_id):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT set_config('app.current_tenant_id', %s, false)",
            (str(tenant_id),),
        )


def test_inventory_tables_have_forced_rls(app_conn):
    tables = (
        "inventory_types",
        "products",
        "inventories",
        "inventory_movements",
    )
    with app_conn.cursor() as cur:
        cur.execute(
            """
            SELECT relname, relrowsecurity, relforcerowsecurity
            FROM pg_class
            WHERE oid IN (
                'users_api.inventory_types'::regclass,
                'users_api.products'::regclass,
                'users_api.inventories'::regclass,
                'users_api.inventory_movements'::regclass
            )
            """
        )
        rows = {row[0]: (row[1], row[2]) for row in cur.fetchall()}

    assert set(rows) == set(tables)
    assert all(enabled and forced for enabled, forced in rows.values())


def test_inventory_rls_does_not_bypass_and_blocks_cross_tenant_insert(
    app_conn,
    bootstrap_conn,
    tenant_ids,
):
    tenant_a, tenant_b = tenant_ids
    suffix = "pytest-rls"

    with bootstrap_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users_api.inventory_types
                (tenant_id, code, name, active, created_by)
            VALUES (%s, %s, %s, true, 'pytest')
            ON CONFLICT (tenant_id, code) DO UPDATE
            SET name = EXCLUDED.name
            RETURNING id
            """,
            (tenant_b, suffix, "RLS Test"),
        )
        type_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO users_api.products
                (tenant_id, inventory_type_id, code, name, active, created_by)
            VALUES (%s, %s, %s, %s, true, 'pytest')
            ON CONFLICT (tenant_id, code) DO UPDATE
            SET name = EXCLUDED.name
            RETURNING id
            """,
            (tenant_b, type_id, suffix, "RLS Test Product"),
        )
        product_id = cur.fetchone()[0]
        bootstrap_conn.commit()

    set_tenant(app_conn, tenant_a)
    with app_conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM users_api.products WHERE tenant_id = %s",
            (tenant_b,),
        )
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user")
        assert cur.fetchone()[0] is False

    try:
        with app_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users_api.inventories
                    (tenant_id, product_id, quantity, created_by)
                VALUES (%s, %s, 1, 'pytest')
                """,
                (tenant_b, product_id),
            )
    except psycopg.errors.InsufficientPrivilege as exc:
        assert exc.sqlstate == "42501"
        app_conn.rollback()
        return

    app_conn.rollback()
    raise AssertionError("RLS allowed an inventory insert for another tenant")
