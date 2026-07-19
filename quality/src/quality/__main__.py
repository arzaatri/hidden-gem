"""Manual entrypoint: `uv run --package quality python -m quality`."""

from config.logging_setup import setup_logging
from config.settings import load_settings
from quality.pipeline import run_quality_checks

if __name__ == "__main__":
    setup_logging("datapull", ["quality"])
    settings = load_settings()
    result = run_quality_checks(settings)
    print(result.model_dump_json(indent=2))
