-- ============================================================
-- USERS API APP
--
-- Rol utilizado por la aplicación normalmente.
-- NO tiene BYPASSRLS.
--
-- USERS_API_APP_PASSWORD se resuelve por el instalador desde
-- el ambiente activo (.env, .env.test o hosting).
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'users_api_app'
    ) THEN
        CREATE ROLE users_api_app
        LOGIN
        PASSWORD '${USERS_API_APP_PASSWORD}'
        NOSUPERUSER
        NOCREATEDB
        NOCREATEROLE
        NOINHERIT
        NOBYPASSRLS;
    ELSE
        -- En Neon el usuario administrativo puede no ser SUPERUSER.
        -- Solo actualizamos atributos que puede modificar sin intentar
        -- cambiar privilegios reservados del rol existente.
        ALTER ROLE users_api_app
        LOGIN
        PASSWORD '${USERS_API_APP_PASSWORD}';
    END IF;
END
$$;

GRANT USAGE
ON SCHEMA users_api
TO users_api_app;

GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA users_api
TO users_api_app;

GRANT USAGE, SELECT
ON ALL SEQUENCES IN SCHEMA users_api
TO users_api_app;

-- Los objetos creados por el instalador/migraciones pertenecen al rol
-- que ejecuta el instalador, por lo que los privilegios por defecto se
-- aplican a CURRENT_USER. Esto evita depender de roles específicos de Neon.
ALTER DEFAULT PRIVILEGES
FOR ROLE CURRENT_USER
IN SCHEMA users_api
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLES
TO users_api_app;

ALTER DEFAULT PRIVILEGES
FOR ROLE CURRENT_USER
IN SCHEMA users_api
GRANT USAGE, SELECT
ON SEQUENCES
TO users_api_app;