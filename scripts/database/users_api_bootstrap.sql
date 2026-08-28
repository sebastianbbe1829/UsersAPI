-- ============================================================
-- USERS API BOOTSTRAP
--
-- Rol utilizado exclusivamente durante bootstrap.
--
-- Este rol puede trabajar sin RLS mediante BYPASSRLS.
-- ============================================================

CREATE ROLE users_api_bootstrap
LOGIN
PASSWORD 'C4MB14M3_2026'
NOSUPERUSER
NOCREATEDB
NOCREATEROLE
INHERIT
BYPASSRLS;


-- ============================================================
-- ACCESO AL SCHEMA
-- ============================================================

GRANT USAGE
ON SCHEMA users_api
TO users_api_bootstrap;


-- ============================================================
-- PERMISOS SOBRE TODAS LAS TABLAS EXISTENTES
-- ============================================================

GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA users_api
TO users_api_bootstrap;


-- ============================================================
-- PERMISOS SOBRE TODAS LAS SECUENCIAS EXISTENTES
-- ============================================================

GRANT USAGE, SELECT
ON ALL SEQUENCES IN SCHEMA users_api
TO users_api_bootstrap;


-- ============================================================
-- PERMISOS PARA OBJETOS FUTUROS
-- ============================================================

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