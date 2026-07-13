"""Recommendation logic: given games a user likes, find hidden gems."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod

from backend.db import GameRepository
from backend.models import Game


class GemFinder(ABC):
    """Recommends hidden gems similar to a user's selected games."""

    def __init__(self, hidden_gem_count: int) -> None:
        self.hidden_gem_count = hidden_gem_count

    @abstractmethod
    def recommend(self, games: list[Game]) -> list[Game]:
        """Returns up to `hidden_gem_count` hidden gems related to `games`."""


class MockGemFinder(GemFinder):
    """Placeholder for the real recommendation model: returns random hidden
    gems sharing at least one genre with the input games."""

    def __init__(self, hidden_gem_count: int, game_repository: GameRepository) -> None:
        super().__init__(hidden_gem_count)
        self._game_repository = game_repository

    def recommend(self, games: list[Game]) -> list[Game]:
        genres = {genre for game in games for genre in game.genres}
        exclude_ids = {game.game_id for game in games}
        candidates = self._game_repository.get_hidden_gems_by_genres(genres, exclude_ids)
        return random.sample(candidates, k=min(self.hidden_gem_count, len(candidates)))
