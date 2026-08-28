-- ============================================================
-- USERS API BOOTSTRAP
--
-- Rol utilizado exclusivamente durante bootstrap.
-- Este rol puede trabajar sin RLS mediante BYPASSRLS.
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'users_api_bootstrap'
    ) THEN
        CREATE ROLE users_api_bootstrap
        LOGIN
        PASSWORD 'C4MB14M3_2026'
        NOSUPERUSER
        NOCREATEDB
        NOCREATEROLE
        INHERIT
        BYPASSRLS;
    END IF;
END
$$;

-- IMPORTANTE:
-- Si el rol ya existe, no se modifican sus atributos aquí.
-- Neon no permite alterar atributos administrativos del rol
-- con la conexión utilizada por la aplicación/instalador.

GRANT USAGE
ON SCHEMA users_api
TO users_api_bootstrap;

GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA users_api
TO users_api_bootstrap;

GRANT USAGE, SELECT
ON ALL SEQUENCES IN SCHEMA users_api
TO users_api_bootstrap;

ALTER DEFAULT PRIVILEGES
FOR ROLE neondb_owner
IN SCHEMA users_api
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLES
TO users_api_bootstrap;

ALTER DEFAULT PRIVILEGES
FOR ROLE neondb_owner
IN SCHEMA users_api
GRANT USAGE, SELECT
ON SEQUENCES
TO users_api_bootstrap;
