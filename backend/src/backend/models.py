"""Pydantic models for the game search / recommendation API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class GameSummary(BaseModel):
    """Lightweight shape used for search-box autocomplete results."""

    game_id: int
    name: str
    genres: list[str]
    cover_image_id: str | None
    first_release_date: datetime | None


class Game(BaseModel):
    """Full gold.dim_games row, used for recommendation results."""

    game_id: int
    name: str
    rating: float | None
    aggregated_rating: float | None
    aggregated_rating_count: int | None
    follows: int | None
    hypes: int | None
    summary: str | None
    storyline: str | None
    cover_image_id: str | None
    first_release_date: datetime | None
    updated_at: datetime
    genres: list[str]
    themes: list[str]
    keywords: list[str]
    hidden_gem: bool


class RecommendRequest(BaseModel):
    game_ids: list[int] = Field(min_length=1)
    hidden_gems_only: bool = True


class Recommendation(BaseModel):
    """A recommended game plus how `ContentBasedGemFinder` arrived at its score.

    `signal_breakdown` maps each of the 7 similarity signals (genre/theme/
    keyword/summary/storyline/cover/screenshots) to its own normalized
    similarity score (0-1) — only signals with data for this pair are
    present. This is raw per-dimension similarity, independent of that
    signal's configured weight, so it does NOT sum to `match_score` (the
    single blended, weighted score used for ranking) — it answers "how
    similar on this axis", not "how much of the total this axis contributed".
    """

    game: Game
    match_score: float
    signal_breakdown: dict[str, float]
