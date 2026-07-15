"""Manual entrypoint: `uv run --package embeddings python -m embeddings`."""

from config.settings import load_settings
from embeddings.pipeline import run_embeddings_pipeline

if __name__ == "__main__":
    settings = load_settings()
    result = run_embeddings_pipeline(settings)
    print(result.model_dump_json(indent=2))
