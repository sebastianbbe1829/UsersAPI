-- ============================================================
-- USERS API APP
--
-- Rol utilizado por la aplicación normalmente.
-- NO tiene BYPASSRLS.
-- ============================================================

CREATE ROLE users_api_app
LOGIN
PASSWORD 'C4MB14M3_2026'
NOSUPERUSER
NOCREATEDB
NOCREATEROLE
NOINHERIT
NOBYPASSRLS;


-- ============================================================
-- ACCESO AL SCHEMA
-- ============================================================

GRANT USAGE
ON SCHEMA users_api
TO users_api_app;


-- ============================================================
-- PERMISOS SOBRE TABLAS EXISTENTES
-- ============================================================

GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA users_api
TO users_api_app;


-- ============================================================
-- PERMISOS SOBRE SECUENCIAS EXISTENTES
--
-- IMPORTANTE:
-- Las tablas con SERIAL/IDENTITY utilizan secuencias.
-- Sin USAGE/SELECT la aplicación puede consultar tablas
-- pero falla al hacer INSERT.
-- ============================================================

GRANT USAGE, SELECT
ON ALL SEQUENCES IN SCHEMA users_api
TO users_api_app;


-- ============================================================
-- PERMISOS PARA OBJETOS FUTUROS
--
-- Alembic normalmente ejecuta las migraciones como
-- neondb_owner, por eso se especifica FOR ROLE neondb_owner.
-- ============================================================

ALTER DEFAULT PRIVILEGES
FOR ROLE neondb_owner
IN SCHEMA users_api
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLES
TO users_api_app;


ALTER DEFAULT PRIVILEGES
FOR ROLE neondb_owner
IN SCHEMA users_api
GRANT USAGE, SELECT
ON SEQUENCES
TO users_api_app;