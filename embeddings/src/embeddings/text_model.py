"""Text embeddings via sentence-transformers, for semantic similarity of
game summaries/storylines."""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


class TextEmbedder:
    def __init__(self) -> None:
        self._model = SentenceTransformer(MODEL_NAME)

    def embed(self, text: str) -> np.ndarray:
        return self._model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
