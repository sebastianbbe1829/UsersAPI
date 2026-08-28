-- ============================================================
-- USERS API APP
--
-- Rol utilizado por la aplicación normalmente.
-- NO tiene BYPASSRLS.
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'users_api_app'
    ) THEN
        CREATE ROLE users_api_app
        LOGIN
        PASSWORD 'C4MB14M3_2026'
        NOSUPERUSER
        NOCREATEDB
        NOCREATEROLE
        NOINHERIT
        NOBYPASSRLS;
    END IF;
END
$$;

ALTER ROLE users_api_app
LOGIN
PASSWORD 'C4MB14M3_2026'
NOSUPERUSER
NOCREATEDB
NOCREATEROLE
NOINHERIT
NOBYPASSRLS;

GRANT USAGE
ON SCHEMA users_api
TO users_api_app;

GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA users_api
TO users_api_app;

GRANT USAGE, SELECT
ON ALL SEQUENCES IN SCHEMA users_api
TO users_api_app;

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
