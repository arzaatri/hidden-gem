"""FastAPI app: game search + "Mine for gems" recommendation, plus the static frontend."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from backend.db import GameRepository
from backend.gem_finder import ContentBasedGemFinder, GemFinder
from backend.models import Game, GameSummary, RecommendRequest
from config.logging_setup import setup_logging
from config.settings import load_settings

STATIC_DIR = Path(__file__).parent.parent.parent / "static"

setup_logging("webapp", ["backend"])
logger = logging.getLogger(__name__)

settings = load_settings()
game_repository = GameRepository(settings.postgres_dsn())
gem_finder: GemFinder = ContentBasedGemFinder(
    settings.recommendation.hidden_gem_count,
    settings.recommendation.rating_cutoff,
    settings.recommendation.weights,
    game_repository,
)

app = FastAPI(title="Hidden Gem API")


@app.get("/api/config")
def get_config() -> dict[str, int]:
    return {
        "max_selected_games": settings.recommendation.max_selected_games,
        "hidden_gem_count": settings.recommendation.hidden_gem_count,
    }


@app.get("/api/games/search")
def search_games(q: str, limit: int = 10) -> list[GameSummary]:
    results = game_repository.search_games(q, limit)
    logger.info('Search %r returned %d result(s)', q, len(results))
    return results


@app.post("/api/recommend")
def recommend(request: RecommendRequest) -> list[Game]:
    max_selected = settings.recommendation.max_selected_games
    if len(request.game_ids) > max_selected:
        raise HTTPException(422, f"Select at most {max_selected} games.")

    games = game_repository.get_games_by_ids(request.game_ids)
    found_ids = {game.game_id for game in games}
    missing_ids = set(request.game_ids) - found_ids
    if missing_ids:
        raise HTTPException(404, f"Unknown game id(s): {sorted(missing_ids)}")

    recommendations = gem_finder.recommend(games, request.hidden_gems_only)
    logger.info(
        "Recommend %s (hidden_gems_only=%s) -> %s",
        [game.game_id for game in games],
        request.hidden_gems_only,
        [game.game_id for game in recommendations],
    )
    return recommendations


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
