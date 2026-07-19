"""Validates the newest bronze IGDB batch against the Great Expectations suite."""

from __future__ import annotations

import logging
from pathlib import Path

import great_expectations as gx
from great_expectations.core.batch_definition import BatchDefinition
from pydantic import BaseModel

from config.settings import Settings
from quality.bronze_reader import get_latest_bronze_batch
from quality.expectations import build_bronze_suite

logger = logging.getLogger(__name__)

QUALITY_PACKAGE_ROOT = Path(__file__).parent.parent.parent

_DATA_SOURCE_NAME = "bronze_games"
_ASSET_NAME = "games"
_BATCH_DEFINITION_NAME = "latest_batch"
_VALIDATION_DEFINITION_NAME = "bronze_games_validation"
_CHECKPOINT_NAME = "bronze_games_checkpoint"


class QualityCheckResult(BaseModel):
    checked: bool
    games_validated: int
    success: bool
    failed_expectations: list[str]


def _get_batch_definition(context: gx.data_context.AbstractDataContext) -> BatchDefinition:
    data_source = context.data_sources.add_or_update_pandas(_DATA_SOURCE_NAME)
    asset = (
        data_source.get_asset(_ASSET_NAME)
        if _ASSET_NAME in data_source.get_asset_names()
        else data_source.add_dataframe_asset(name=_ASSET_NAME)
    )
    existing = next((bd for bd in asset.batch_definitions if bd.name == _BATCH_DEFINITION_NAME), None)
    return existing or asset.add_batch_definition_whole_dataframe(_BATCH_DEFINITION_NAME)


def _get_checkpoint(context: gx.data_context.AbstractDataContext) -> gx.Checkpoint:
    suite = context.suites.add_or_update(build_bronze_suite())
    batch_definition = _get_batch_definition(context)
    validation_definition = context.validation_definitions.add_or_update(
        gx.ValidationDefinition(name=_VALIDATION_DEFINITION_NAME, data=batch_definition, suite=suite)
    )
    return context.checkpoints.add_or_update(
        gx.Checkpoint(
            name=_CHECKPOINT_NAME,
            validation_definitions=[validation_definition],
            actions=[gx.checkpoint.UpdateDataDocsAction(name="update_data_docs")],
        )
    )


def run_quality_checks(settings: Settings) -> QualityCheckResult:
    batch = get_latest_bronze_batch(settings.minio, settings.secrets)
    if batch is None:
        logger.info("No bronze data to validate")
        return QualityCheckResult(checked=False, games_validated=0, success=True, failed_expectations=[])

    # gx.get_context(mode="file", ...) itself creates a "gx/" subdirectory
    # inside project_root_dir, so passing the quality/ package root here
    # lands the generated project (suites, checkpoints, Data Docs) at
    # quality/gx/ — not quality/gx/gx/.
    context = gx.get_context(mode="file", project_root_dir=QUALITY_PACKAGE_ROOT)
    checkpoint = _get_checkpoint(context)
    result = checkpoint.run(batch_parameters={"dataframe": batch})

    failed_expectations = [
        expectation["expectation_type"]
        for validation_result in result.describe_dict()["validation_results"]
        for expectation in validation_result["expectations"]
        if not expectation["success"]
    ]

    if result.success:
        logger.info("Bronze batch passed all expectations (%d games)", len(batch))
    else:
        logger.warning(
            "Bronze batch failed expectations %s (%d games)", failed_expectations, len(batch)
        )

    return QualityCheckResult(
        checked=True,
        games_validated=len(batch),
        success=result.success,
        failed_expectations=failed_expectations,
    )
