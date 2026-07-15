"""Reads/writes precomputed embeddings in Postgres (pgvector columns)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from embeddings.image_model import EMBEDDING_DIM as IMAGE_EMBEDDING_DIM
from embeddings.text_model import EMBEDDING_DIM as TEXT_EMBEDDING_DIM

_BOOTSTRAP_SQL = f"""
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS embeddings;
CREATE TABLE IF NOT EXISTS embeddings.game_embeddings (
    game_id bigint PRIMARY KEY,
    summary_embedding vector({TEXT_EMBEDDING_DIM}),
    storyline_embedding vector({TEXT_EMBEDDING_DIM}),
    cover_embedding vector({IMAGE_EMBEDDING_DIM}),
    screenshots_embedding vector({IMAGE_EMBEDDING_DIM}),
    embedded_at timestamptz NOT NULL
);
"""

_GAMES_NEEDING_EMBEDDINGS_SQL = """
    SELECT g.game_id, g.summary, g.storyline, g.cover_image_id, g.updated_at
    FROM gold.dim_games g
    LEFT JOIN embeddings.game_embeddings e ON e.game_id = g.game_id
    WHERE e.game_id IS NULL OR g.updated_at > e.embedded_at
"""

_UPSERT_SQL = """
    INSERT INTO embeddings.game_embeddings
        (game_id, summary_embedding, storyline_embedding, cover_embedding, screenshots_embedding, embedded_at)
    VALUES (%(game_id)s, %(summary_embedding)s, %(storyline_embedding)s, %(cover_embedding)s, %(screenshots_embedding)s, now())
    ON CONFLICT (game_id) DO UPDATE SET
        summary_embedding = EXCLUDED.summary_embedding,
        storyline_embedding = EXCLUDED.storyline_embedding,
        cover_embedding = EXCLUDED.cover_embedding,
        screenshots_embedding = EXCLUDED.screenshots_embedding,
        embedded_at = EXCLUDED.embedded_at
"""


@dataclass
class GameNeedingEmbedding:
    game_id: int
    summary: str | None
    storyline: str | None
    cover_image_id: str | None
    updated_at: datetime


@dataclass
class GameEmbeddingVectors:
    game_id: int
    summary_embedding: np.ndarray | None
    storyline_embedding: np.ndarray | None
    cover_embedding: np.ndarray | None
    screenshots_embedding: np.ndarray | None


def ensure_embeddings_table(dsn: str) -> None:
    with psycopg.connect(dsn) as conn:
        conn.execute(_BOOTSTRAP_SQL)


def get_games_needing_embeddings(dsn: str) -> list[GameNeedingEmbedding]:
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        rows = conn.execute(_GAMES_NEEDING_EMBEDDINGS_SQL).fetchall()
    return [GameNeedingEmbedding(**row) for row in rows]


def upsert_embedding(dsn: str, vectors: GameEmbeddingVectors) -> None:
    with psycopg.connect(dsn) as conn:
        register_vector(conn)
        conn.execute(
            _UPSERT_SQL,
            {
                "game_id": vectors.game_id,
                "summary_embedding": vectors.summary_embedding,
                "storyline_embedding": vectors.storyline_embedding,
                "cover_embedding": vectors.cover_embedding,
                "screenshots_embedding": vectors.screenshots_embedding,
            },
        )
