CREATE SCHEMA IF NOT EXISTS users_api;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'users_api_app'
    ) THEN
        CREATE ROLE users_api_app
        LOGIN
        NOSUPERUSER
        NOCREATEDB
        NOCREATEROLE
        NOINHERIT
        NOBYPASSRLS;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'users_api_bootstrap'
    ) THEN
        CREATE ROLE users_api_bootstrap
        LOGIN
        NOSUPERUSER
        NOCREATEDB
        NOCREATEROLE
        INHERIT
        BYPASSRLS;
    END IF;
END
$$;

GRANT USAGE ON SCHEMA users_api TO users_api_app;
GRANT USAGE ON SCHEMA users_api TO users_api_bootstrap;
