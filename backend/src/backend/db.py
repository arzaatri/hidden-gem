"""Read-only data access against gold.dim_games for the API layer."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from backend.models import Game, GameSummary

_SEARCH_SQL = """
    SELECT game_id, name, genres, cover_image_id, first_release_date
    FROM gold.dim_games
    WHERE name ILIKE %(pattern)s
    ORDER BY name
    LIMIT %(limit)s
"""

_GET_BY_IDS_SQL = "SELECT * FROM gold.dim_games WHERE game_id = ANY(%(game_ids)s)"

_GAMES_BY_GENRE_SQL = """
    SELECT * FROM gold.dim_games
    WHERE (NOT %(hidden_gems_only)s OR hidden_gem)
      AND genres::text[] && %(genres)s::text[]
      AND NOT (game_id = ANY(%(exclude_ids)s))
"""

_CANDIDATE_POOL_SQL = """
    SELECT * FROM gold.dim_games
    WHERE (NOT %(hidden_gems_only)s OR hidden_gem)
      AND (aggregated_rating IS NULL OR aggregated_rating >= %(rating_cutoff)s)
      AND NOT (game_id = ANY(%(exclude_ids)s))
"""

_TAG_IDF_SQL = "SELECT tag_category, tag_value, idf FROM gold.tag_idf"

_GET_EMBEDDINGS_SQL = """
    SELECT game_id, summary_embedding, storyline_embedding, cover_embedding, screenshots_embedding
    FROM embeddings.game_embeddings
    WHERE game_id = ANY(%(game_ids)s)
"""


@dataclass
class GameEmbeddings:
    game_id: int
    summary_embedding: np.ndarray | None
    storyline_embedding: np.ndarray | None
    cover_embedding: np.ndarray | None
    screenshots_embedding: np.ndarray | None


class GameRepository:
    """Encapsulates every SQL query the API needs against gold.dim_games."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def search_games(self, query: str, limit: int = 10) -> list[GameSummary]:
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            rows = conn.execute(_SEARCH_SQL, {"pattern": f"%{query}%", "limit": limit}).fetchall()
        return [GameSummary(**row) for row in rows]

    def get_games_by_ids(self, game_ids: list[int]) -> list[Game]:
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            rows = conn.execute(_GET_BY_IDS_SQL, {"game_ids": game_ids}).fetchall()
        return [Game(**row) for row in rows]

    def get_games_by_genres(
        self, genres: set[str], exclude_ids: set[int], hidden_gems_only: bool
    ) -> list[Game]:
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            rows = conn.execute(
                _GAMES_BY_GENRE_SQL,
                {
                    "genres": list(genres),
                    "exclude_ids": list(exclude_ids),
                    "hidden_gems_only": hidden_gems_only,
                },
            ).fetchall()
        return [Game(**row) for row in rows]

    def get_candidate_pool(
        self, exclude_ids: set[int], hidden_gems_only: bool, rating_cutoff: int
    ) -> list[Game]:
        """Eligible recommendation candidates: no genre requirement (genre is a
        scored signal, not a gate) — just the hard hidden_gem/rating/exclude filters."""
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            rows = conn.execute(
                _CANDIDATE_POOL_SQL,
                {
                    "exclude_ids": list(exclude_ids),
                    "hidden_gems_only": hidden_gems_only,
                    "rating_cutoff": rating_cutoff,
                },
            ).fetchall()
        return [Game(**row) for row in rows]

    def get_tag_idf(self) -> dict[str, dict[str, float]]:
        """category -> tag_value -> idf, from gold.tag_idf."""
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            rows = conn.execute(_TAG_IDF_SQL).fetchall()
        idf_by_category: dict[str, dict[str, float]] = {}
        for row in rows:
            idf_by_category.setdefault(row["tag_category"], {})[row["tag_value"]] = row["idf"]
        return idf_by_category

    def get_embeddings(self, game_ids: set[int]) -> dict[int, GameEmbeddings]:
        with psycopg.connect(self._dsn) as conn:
            register_vector(conn)
            with conn.cursor(row_factory=dict_row) as cur:
                rows = cur.execute(_GET_EMBEDDINGS_SQL, {"game_ids": list(game_ids)}).fetchall()
        return {
            row["game_id"]: GameEmbeddings(
                game_id=row["game_id"],
                summary_embedding=_to_numpy(row["summary_embedding"]),
                storyline_embedding=_to_numpy(row["storyline_embedding"]),
                cover_embedding=_to_numpy(row["cover_embedding"]),
                screenshots_embedding=_to_numpy(row["screenshots_embedding"]),
            )
            for row in rows
        }


def _to_numpy(vector) -> np.ndarray | None:
    return vector.to_numpy() if vector is not None else None
