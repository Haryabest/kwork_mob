-- §12.1 Logical replication user + publication for Debezium
-- Run once on primary: psql -U kwork -d kwork_mob -f infra/postgres/debezium_init.sql

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'debezium') THEN
    CREATE ROLE debezium WITH REPLICATION LOGIN PASSWORD 'debezium_change_me';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE kwork_mob TO debezium;
GRANT USAGE ON SCHEMA public TO debezium;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO debezium;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO debezium;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'dbz_user_events') THEN
    CREATE PUBLICATION dbz_user_events FOR TABLE user_events, orders, models_3d;
  END IF;
END
$$;
