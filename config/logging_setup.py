"""Shared logging setup: one line format across all services, files under logs/<service>/.

Call `setup_logging(service, packages)` once near the top of each process
entrypoint, naming the top-level package(s) whose loggers should be captured
— e.g. `setup_logging("datapull", ["extraction", "embeddings"])` in Dagster,
`setup_logging("webapp", ["backend"])` in the FastAPI app. Only those packages'
loggers are configured (not the root logger), so framework loggers (Dagster,
uvicorn) keep their own output instead of getting captured and reprinted in
our format.

Everywhere else, just use `logging.getLogger(__name__)` as normal: the dotted
module path becomes the "module.submodule" part of the line, and the calling
function name is appended automatically, e.g.:

    [2026-07-16 01:04:44.593 UTC][extraction.pipeline.run_extraction] Pulled 87 games
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

LOGS_DIR = Path(__file__).parent.parent / "logs"

_FORMAT = "[%(asctime)s.%(msecs)03d UTC][%(name)s.%(funcName)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(service: str, packages: list[str], level: int = logging.INFO) -> None:
    log_dir = LOGS_DIR / service
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT)
    formatter.converter = time.gmtime  # log in UTC regardless of the host/container's local timezone

    file_handler = logging.FileHandler(log_dir / f"{service}.log")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    for package in packages:
        package_logger = logging.getLogger(package)
        if package_logger.handlers:
            continue  # already configured in this process

        package_logger.setLevel(level)
        package_logger.addHandler(file_handler)
        package_logger.addHandler(stream_handler)
        package_logger.propagate = False  # don't also hand records to the root logger
