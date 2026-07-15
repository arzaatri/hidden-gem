-- Enables the pgvector extension (image is pgvector/pgvector, which bundles
-- it) so embeddings.game_embeddings can use `vector(n)` columns.
CREATE EXTENSION IF NOT EXISTS vector;
