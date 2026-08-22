-- RLS integration checks
-- Ejecutar conectado como users_api_app.
-- Sustituir <TENANT_A> y <TENANT_B> por dos tenants existentes.
-- El objetivo es validar que el contexto de tenant limita SELECT/INSERT/UPDATE/DELETE.

-- 1. Contexto A debe quedar establecido.
SELECT set_config('app.current_tenant_id', '<TENANT_A>', false);
SELECT current_setting('app.current_tenant_id', true) AS tenant_context;

-- 2. Solo deben ser visibles filas del tenant A.
SELECT id, tenant_id
FROM users_api.user_tenants
WHERE tenant_id = '<TENANT_A>';

SELECT id, tenant_id
FROM users_api.user_tenants
WHERE tenant_id = '<TENANT_B>';
-- Esperado: 0 filas.

-- 3. Intento de INSERT para tenant B debe ser rechazado por RLS.
-- Ejecutar como sentencia individual; debe fallar con SQLSTATE 42501.
-- INSERT INTO users_api.user_tenants (user_id, tenant_id, status)
-- VALUES (<USER_ID>, <TENANT_B>, 0);

-- 4. Cambiar a tenant B y comprobar aislamiento.
SELECT set_config('app.current_tenant_id', '<TENANT_B>', false);
SELECT id, tenant_id
FROM users_api.user_tenants
WHERE tenant_id = '<TENANT_A>';
-- Esperado: 0 filas.

-- 5. Limpiar contexto al terminar.
SELECT set_config('app.current_tenant_id', '', false);
