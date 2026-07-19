from dagster import AssetSelection, Definitions, define_asset_job
from dagster_dbt import DbtCliResource

from config.logging_setup import setup_logging
from orchestration.assets.bronze import raw_games
from orchestration.assets.embeddings import game_embeddings
from orchestration.assets.quality import ge_bronze_expectations
from orchestration.dbt import dbt_models, dbt_project
from orchestration.schedules import build_daily_schedule

# Dagster loads this module once per code-server process, so this is the one
# place to configure logging for the asset code (extraction + embeddings +
# quality, i.e. the "datapull" side) that runs inside it.
setup_logging("datapull", ["extraction", "embeddings", "quality"])

daily_hidden_gem_sync = define_asset_job(
    name="daily_hidden_gem_sync",
    selection=AssetSelection.all(),
)

defs = Definitions(
    assets=[raw_games, dbt_models, game_embeddings],
    asset_checks=[ge_bronze_expectations],
    resources={"dbt": DbtCliResource(project_dir=dbt_project)},
    jobs=[daily_hidden_gem_sync],
    schedules=[build_daily_schedule(daily_hidden_gem_sync)],
)
