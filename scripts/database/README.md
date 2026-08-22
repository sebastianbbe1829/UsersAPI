# Database security scripts

Esta carpeta contiene scripts operativos de PostgreSQL relacionados con la seguridad de la base de datos.

- `01_create_database_roles.sql`: creación de `users_api_app` y `users_api_bootstrap`.
- `02_grant_database_permissions.sql`: permisos de conexión, esquema y objetos necesarios.
- `03_rls_policies.sql`: referencia de políticas RLS y configuración asociada.

Estos scripts no sustituyen las migraciones de Alembic. Las migraciones versionadas son la fuente de verdad para cambios de esquema reproducibles; estos archivos sirven como documentación/operación de la seguridad de PostgreSQL.

**Importante:** no almacenar contraseñas reales en estos archivos. Usar placeholders y variables/secretos del entorno.
