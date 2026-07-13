"""Pydantic models for the game search / recommendation API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class GameSummary(BaseModel):
    """Lightweight shape used for search-box autocomplete results."""

    game_id: int
    name: str
    genres: list[str]


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
    updated_at: datetime
    genres: list[str]
    themes: list[str]
    keywords: list[str]
    hidden_gem: bool


class RecommendRequest(BaseModel):
    game_ids: list[int] = Field(min_length=1)
