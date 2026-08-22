# Tests automatizados de RLS

Estos tests se ejecutan contra PostgreSQL/Neon real porque SQLite no reproduce RLS de PostgreSQL.

## Preparación

La terminal debe tener configuradas las variables:

- `DATABASE_URL`: conexión con `users_api_app`.
- `BOOTSTRAP_DATABASE_URL`: conexión con `users_api_bootstrap`.

No guardar credenciales en el repositorio.

## Ejecución

Desde la raíz del proyecto:

```powershell
pytest test/rls -v
```

Los tests usan transacciones/conexiones aisladas y no deben dejar datos creados por la prueba de INSERT.

## Cobertura

- `test_rls_isolation.py`: RLS habilitado/forzado, rol de aplicación sin BYPASSRLS, aislamiento entre tenants y bloqueo de INSERT cruzado.
- `test_bootstrap_rls.py`: rol bootstrap con BYPASSRLS y operación sin contexto de tenant.
- `test_tenant_resolver.py`: resolución del tenant mediante token y establecimiento posterior del contexto para el rol de aplicación.
