-- Activación sin JWT / sin contexto previo de tenant.
-- Este flujo debe resolver el tenant usando exclusivamente el activation_token
-- antes de consultar/modificar user_tenants bajo RLS.

-- 1. Validar que el resolver encuentra el tenant asociado al token.
SELECT users_api.resolve_tenant_id_by_activation_token('<ACTIVATION_TOKEN>') AS tenant_id;

-- 2. Con el tenant resuelto, establecer contexto y verificar la asociación.
SELECT set_config(
    'app.current_tenant_id',
    users_api.resolve_tenant_id_by_activation_token('<ACTIVATION_TOKEN>')::text,
    false
);

SELECT id, user_id, tenant_id, status, activation_token
FROM users_api.user_tenants
WHERE activation_token = '<ACTIVATION_TOKEN>';

-- Esperado: exactamente la asociación que contiene el token.

SELECT set_config('app.current_tenant_id', '', false);
