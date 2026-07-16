"""Manual entrypoint: `uv run python -m extraction`."""

from config.logging_setup import setup_logging
from config.settings import load_settings
from extraction.pipeline import run_extraction

if __name__ == "__main__":
    setup_logging("datapull", ["extraction"])
    settings = load_settings()
    result = run_extraction(settings)
    print(result.model_dump_json(indent=2))
