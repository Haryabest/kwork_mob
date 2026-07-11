-- Инициализация PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Роли по умолчанию
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    permissions JSONB NOT NULL DEFAULT '{}'
);

INSERT INTO roles (name, permissions) VALUES
    ('owner', '{"all": true}'),
    ('manager', '{"invite": true, "view_orders": true}'),
    ('photographer', '{"create_order": true, "shoot": true}'),
    ('viewer', '{"view_models": true}')
ON CONFLICT (name) DO NOTHING;
