"""dbt-duckdb project wiring: exposes the whole dbt DAG as Dagster assets."""

import json
from pathlib import Path

from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

from config.settings import load_settings

DBT_PROJECT_DIR = Path(__file__).parent.parent.parent.parent / "dbt_project"

dbt_project = DbtProject(project_dir=DBT_PROJECT_DIR)
dbt_project.prepare_if_dev()


@dbt_assets(manifest=dbt_project.manifest_path)
def dbt_models(context: AssetExecutionContext, dbt: DbtCliResource):
    # Single source of truth for the hidden_gem percentile: settings.yaml,
    # not dbt_project.yml's fallback default.
    settings = load_settings()
    dbt_vars = {"hidden_gem_rating_count_percentile": settings.etl.hidden_gem_rating_count_percentile}
    yield from dbt.cli(["build", "--vars", json.dumps(dbt_vars)], context=context).stream()
