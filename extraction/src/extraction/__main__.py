"""Manual entrypoint: `uv run python -m extraction`."""

from config.settings import load_settings
from extraction.pipeline import run_extraction

if __name__ == "__main__":
    settings = load_settings()
    result = run_extraction(settings)
    print(result.model_dump_json(indent=2))
