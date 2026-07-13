"""Read-only data access against gold.dim_games for the API layer."""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from backend.models import Game, GameSummary

_SEARCH_SQL = """
    SELECT game_id, name, genres
    FROM gold.dim_games
    WHERE name ILIKE %(pattern)s
    ORDER BY name
    LIMIT %(limit)s
"""

_GET_BY_IDS_SQL = "SELECT * FROM gold.dim_games WHERE game_id = ANY(%(game_ids)s)"

_HIDDEN_GEMS_BY_GENRE_SQL = """
    SELECT * FROM gold.dim_games
    WHERE hidden_gem
      AND genres::text[] && %(genres)s::text[]
      AND NOT (game_id = ANY(%(exclude_ids)s))
"""


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

    def get_hidden_gems_by_genres(self, genres: set[str], exclude_ids: set[int]) -> list[Game]:
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            rows = conn.execute(
                _HIDDEN_GEMS_BY_GENRE_SQL,
                {"genres": list(genres), "exclude_ids": list(exclude_ids)},
            ).fetchall()
        return [Game(**row) for row in rows]
