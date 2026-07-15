"""Recommendation logic: given games a user likes, find hidden gems."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod

from config.settings import ContentWeights

from backend.content_scoring import cosine_similarity, normalize, weighted_average, weighted_jaccard
from backend.db import GameEmbeddings, GameRepository
from backend.models import Game


class GemFinder(ABC):
    """Recommends games similar to a user's selected games."""

    def __init__(self, hidden_gem_count: int) -> None:
        self.hidden_gem_count = hidden_gem_count

    @abstractmethod
    def recommend(self, games: list[Game], hidden_gems_only: bool = True) -> list[Game]:
        """Returns up to `hidden_gem_count` games related to `games`.

        When `hidden_gems_only` is True (the default), only games flagged as
        hidden gems are eligible; otherwise any related game is eligible.
        """


class MockGemFinder(GemFinder):
    """Placeholder for the real recommendation model: returns random games
    sharing at least one genre with the input games."""

    def __init__(self, hidden_gem_count: int, game_repository: GameRepository) -> None:
        super().__init__(hidden_gem_count)
        self._game_repository = game_repository

    def recommend(self, games: list[Game], hidden_gems_only: bool = True) -> list[Game]:
        genres = {genre for game in games for genre in game.genres}
        exclude_ids = {game.game_id for game in games}
        candidates = self._game_repository.get_games_by_genres(genres, exclude_ids, hidden_gems_only)
        return random.sample(candidates, k=min(self.hidden_gem_count, len(candidates)))


class ContentBasedGemFinder(GemFinder):
    """Scores candidates on 7 similarity signals — IDF-weighted Jaccard over
    genres/themes/keywords, embedding cosine similarity over summary/
    storyline/cover art/screenshots — combined into one flat weighted score.
    See config/settings.yaml: recommendation.weights."""

    def __init__(
        self,
        hidden_gem_count: int,
        rating_cutoff: int,
        weights: ContentWeights,
        game_repository: GameRepository,
    ) -> None:
        super().__init__(hidden_gem_count)
        self._rating_cutoff = rating_cutoff
        self._weights = weights.model_dump()
        self._game_repository = game_repository

    def recommend(self, games: list[Game], hidden_gems_only: bool = True) -> list[Game]:
        query_ids = {game.game_id for game in games}
        candidates = self._game_repository.get_candidate_pool(
            query_ids, hidden_gems_only, self._rating_cutoff
        )
        if not candidates:
            return []

        idf = self._game_repository.get_tag_idf()
        embeddings = self._game_repository.get_embeddings(query_ids | {c.game_id for c in candidates})

        pairs = [(query, candidate) for query in games for candidate in candidates]
        raw_signals = [self._raw_signals(query, candidate, idf, embeddings) for query, candidate in pairs]
        normalized_signals = _normalize_all_signals(raw_signals)

        best_score: dict[int, float] = {}
        for (_, candidate), signals in zip(pairs, normalized_signals):
            score = weighted_average(signals, self._weights)
            best_score[candidate.game_id] = max(best_score.get(candidate.game_id, 0.0), score)

        ranked = sorted(candidates, key=lambda candidate: best_score[candidate.game_id], reverse=True)
        return ranked[: self.hidden_gem_count]

    @staticmethod
    def _raw_signals(
        query: Game,
        candidate: Game,
        idf: dict[str, dict[str, float]],
        embeddings: dict[int, GameEmbeddings],
    ) -> dict[str, float | None]:
        query_embedding = embeddings.get(query.game_id)
        candidate_embedding = embeddings.get(candidate.game_id)

        def embedding_similarity(field: str) -> float | None:
            query_vector = getattr(query_embedding, field, None)
            candidate_vector = getattr(candidate_embedding, field, None)
            return cosine_similarity(query_vector, candidate_vector)

        return {
            "genre": weighted_jaccard(set(query.genres), set(candidate.genres), idf.get("genre", {})),
            "theme": weighted_jaccard(set(query.themes), set(candidate.themes), idf.get("theme", {})),
            "keyword": weighted_jaccard(
                set(query.keywords), set(candidate.keywords), idf.get("keyword", {})
            ),
            "summary": embedding_similarity("summary_embedding"),
            "storyline": embedding_similarity("storyline_embedding"),
            "cover": embedding_similarity("cover_embedding"),
            "screenshots": embedding_similarity("screenshots_embedding"),
        }


def _normalize_all_signals(
    raw_signals: list[dict[str, float | None]],
) -> list[dict[str, float | None]]:
    """Normalizes each of the 7 signals across every pair in this request."""
    if not raw_signals:
        return []
    signal_names = raw_signals[0].keys()
    normalized_by_name = {
        name: normalize([signals[name] for signals in raw_signals]) for name in signal_names
    }
    return [
        {name: normalized_by_name[name][i] for name in signal_names}
        for i in range(len(raw_signals))
    ]
