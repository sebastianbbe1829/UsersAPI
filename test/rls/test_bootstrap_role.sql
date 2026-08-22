-- Bootstrap role checks
-- Ejecutar conectado como users_api_bootstrap.

SELECT current_user, session_user;

SELECT rolname, rolbypassrls
FROM pg_roles
WHERE rolname IN ('users_api_app', 'users_api_bootstrap');

-- Esperado:
-- users_api_app       | false
-- users_api_bootstrap | true

-- El bootstrap debe poder operar sin app.current_tenant_id.
SELECT set_config('app.current_tenant_id', '', false);

-- Comprobación de lectura global.
SELECT id, slug, status
FROM users_api.tenants
ORDER BY id;

-- No hacer INSERT/UPDATE/DELETE destructivos en este test.
