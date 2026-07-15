-- Runs once, on first container start (docker-entrypoint-initdb.d), against
-- the POSTGRES_DB created by the postgres image. Each schema is owned by a
-- different concern: gold = analytics output, etl_state = pipeline watermark,
-- dagster = Dagster's own run/schedule storage, embeddings = precomputed
-- CV/NLP vectors for content-based recommendations.
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS etl_state;
CREATE SCHEMA IF NOT EXISTS dagster;
CREATE SCHEMA IF NOT EXISTS embeddings;
