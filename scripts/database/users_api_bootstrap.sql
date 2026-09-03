-- ============================================================
-- USERS API BOOTSTRAP
--
-- Rol utilizado exclusivamente durante bootstrap.
-- Este rol puede trabajar sin RLS mediante BYPASSRLS.
--
-- USERS_API_BOOTSTRAP_PASSWORD se resuelve por el instalador
-- desde el ambiente activo (.env, .env.test o hosting).
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'users_api_bootstrap'
    ) THEN
        CREATE ROLE users_api_bootstrap
        LOGIN
        PASSWORD '${USERS_API_BOOTSTRAP_PASSWORD}'
        NOSUPERUSER
        NOCREATEDB
        NOCREATEROLE
        INHERIT
        BYPASSRLS;
    ELSE
        ALTER ROLE users_api_bootstrap
        LOGIN
        PASSWORD '${USERS_API_BOOTSTRAP_PASSWORD}'
        NOSUPERUSER
        NOCREATEDB
        NOCREATEROLE
        INHERIT
        BYPASSRLS;
    END IF;
END
$$;

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
