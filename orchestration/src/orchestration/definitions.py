from dagster import AssetSelection, Definitions, define_asset_job
from dagster_dbt import DbtCliResource

from orchestration.assets.bronze import raw_games
from orchestration.dbt import dbt_models, dbt_project
from orchestration.schedules import build_daily_schedule

daily_hidden_gem_sync = define_asset_job(
    name="daily_hidden_gem_sync",
    selection=AssetSelection.all(),
)

defs = Definitions(
    assets=[raw_games, dbt_models],
    resources={"dbt": DbtCliResource(project_dir=dbt_project)},
    jobs=[daily_hidden_gem_sync],
    schedules=[build_daily_schedule(daily_hidden_gem_sync)],
)
