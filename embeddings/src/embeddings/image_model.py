"""Image embeddings via CLIP, for visual similarity of cover art/screenshots."""

from __future__ import annotations

import io

import numpy as np
import requests
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

MODEL_NAME = "openai/clip-vit-base-patch32"
EMBEDDING_DIM = 512


def fetch_image(url: str) -> Image.Image:
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return Image.open(io.BytesIO(response.content)).convert("RGB")


class ImageEmbedder:
    def __init__(self) -> None:
        self._model = CLIPModel.from_pretrained(MODEL_NAME)
        self._processor = CLIPProcessor.from_pretrained(MODEL_NAME)

    def embed(self, image: Image.Image) -> np.ndarray:
        inputs = self._processor(images=image, return_tensors="pt")
        output = self._model.get_image_features(**inputs)
        # Some transformers versions wrap the feature tensor in a model
        # output object instead of returning it directly.
        features = output.pooler_output if hasattr(output, "pooler_output") else output
        vector = features.detach().numpy()[0]
        return vector / np.linalg.norm(vector)
