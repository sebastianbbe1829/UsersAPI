GRANT USAGE ON SCHEMA users_api TO users_api_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA users_api TO users_api_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA users_api TO users_api_app;

GRANT USAGE ON SCHEMA users_api TO users_api_bootstrap;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA users_api TO users_api_bootstrap;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA users_api TO users_api_bootstrap;
