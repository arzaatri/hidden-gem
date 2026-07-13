-- Runs once, on first container start (docker-entrypoint-initdb.d), against
-- the POSTGRES_DB created by the postgres image. Each schema is owned by a
-- different concern: gold = analytics output, etl_state = pipeline watermark,
-- dagster = Dagster's own run/schedule storage.
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS etl_state;
CREATE SCHEMA IF NOT EXISTS dagster;
