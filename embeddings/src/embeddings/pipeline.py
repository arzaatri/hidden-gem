"""Orchestrates: find games needing embeddings -> embed text/images -> upsert."""

from __future__ import annotations

import logging

import numpy as np
from pydantic import BaseModel

from config.settings import Settings
from embeddings.igdb_images import igdb_image_url
from embeddings.image_model import ImageEmbedder, fetch_image
from embeddings.silver_reader import read_screenshot_urls
from embeddings.store import (
    GameEmbeddingVectors,
    GameNeedingEmbedding,
    ensure_embeddings_table,
    get_games_needing_embeddings,
    upsert_embedding,
)
from embeddings.text_model import TextEmbedder

logger = logging.getLogger(__name__)

# Cap screenshots embedded per game: bounds pipeline cost, and a handful of
# screenshots is plenty to represent a game's visual style.
MAX_SCREENSHOTS_PER_GAME = 3


class EmbeddingsResult(BaseModel):
    games_embedded: int


def _embed_text_field(embedder: TextEmbedder, text: str | None) -> np.ndarray | None:
    return embedder.embed(text) if text else None


def _embed_cover(embedder: ImageEmbedder, cover_image_id: str | None) -> np.ndarray | None:
    if not cover_image_id:
        return None
    try:
        image = fetch_image(igdb_image_url(cover_image_id, "cover_big"))
        return embedder.embed(image)
    except Exception:
        logger.warning("Failed to embed cover art %s", cover_image_id, exc_info=True)
        return None


def _embed_screenshots(embedder: ImageEmbedder, urls: list[str]) -> np.ndarray | None:
    vectors = []
    for url in urls[:MAX_SCREENSHOTS_PER_GAME]:
        try:
            vectors.append(embedder.embed(fetch_image(url)))
        except Exception:
            logger.warning("Failed to embed screenshot %s", url, exc_info=True)
    if not vectors:
        return None
    average = np.mean(vectors, axis=0)
    return average / np.linalg.norm(average)


def _embed_game(
    game: GameNeedingEmbedding,
    screenshot_urls: list[str],
    text_embedder: TextEmbedder,
    image_embedder: ImageEmbedder,
) -> GameEmbeddingVectors:
    return GameEmbeddingVectors(
        game_id=game.game_id,
        summary_embedding=_embed_text_field(text_embedder, game.summary),
        storyline_embedding=_embed_text_field(text_embedder, game.storyline),
        cover_embedding=_embed_cover(image_embedder, game.cover_image_id),
        screenshots_embedding=_embed_screenshots(image_embedder, screenshot_urls),
    )


def run_embeddings_pipeline(settings: Settings) -> EmbeddingsResult:
    dsn = settings.postgres_dsn()
    ensure_embeddings_table(dsn)

    games = get_games_needing_embeddings(dsn)
    if not games:
        return EmbeddingsResult(games_embedded=0)

    screenshot_urls = read_screenshot_urls(settings.minio, settings.secrets)
    text_embedder = TextEmbedder()
    image_embedder = ImageEmbedder()

    for game in games:
        vectors = _embed_game(game, screenshot_urls.get(game.game_id, []), text_embedder, image_embedder)
        upsert_embedding(dsn, vectors)

    return EmbeddingsResult(games_embedded=len(games))
