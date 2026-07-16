"""Typed application settings.

Non-secret, tunable values come from settings.yaml. Secrets come from the
environment (.env). Both are merged into a single `Settings` object so the
rest of the codebase has one place to import config from.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SETTINGS_YAML = Path(__file__).parent / "settings.yaml"
DEFAULT_ENV_FILE = Path(__file__).parent.parent / ".env"


class EtlConfig(BaseModel):
    max_games: int
    hidden_gem_rating_count_percentile: float
    schedule_cron: str


class ContentWeights(BaseModel):
    """Flat weights for ContentBasedGemFinder's 7 similarity signals."""

    genre: float
    theme: float
    keyword: float
    summary: float
    storyline: float
    cover: float
    screenshots: float

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> "ContentWeights":
        total = sum(self.model_dump().values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"recommendation.weights must sum to 1, got {total}")
        return self


class RecommendationConfig(BaseModel):
    hidden_gem_count: int
    max_selected_games: int
    rating_cutoff: int
    weights: ContentWeights


class MinioConfig(BaseModel):
    endpoint: str
    bucket: str
    bronze_prefix: str
    silver_prefix: str
    use_ssl: bool


class PostgresConfig(BaseModel):
    host: str
    port: int
    gold_schema: str
    etl_state_schema: str
    dagster_schema: str


class IgdbConfig(BaseModel):
    api_base_url: str
    auth_url: str
    fields: list[str]
    page_size: int
    requests_per_second: float


class Secrets(BaseSettings):
    """Loaded from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=DEFAULT_ENV_FILE, extra="ignore")

    igdb_client_id: str = Field(validation_alias="IGDB_CLIENT_ID")
    igdb_client_secret: str = Field(validation_alias="IGDB_CLIENT_SECRET")
    minio_root_user: str = Field(validation_alias="MINIO_ROOT_USER")
    minio_root_password: str = Field(validation_alias="MINIO_ROOT_PASSWORD")
    postgres_user: str = Field(validation_alias="POSTGRES_USER")
    postgres_password: str = Field(validation_alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(validation_alias="POSTGRES_DB")


class Settings(BaseModel):
    etl: EtlConfig
    recommendation: RecommendationConfig
    minio: MinioConfig
    postgres: PostgresConfig
    igdb: IgdbConfig
    secrets: Secrets

    def postgres_dsn(self, schema: str | None = None) -> str:
        dsn = (
            f"postgresql://{self.secrets.postgres_user}:{self.secrets.postgres_password}"
            f"@{self.postgres.host}:{self.postgres.port}/{self.secrets.postgres_db}"
        )
        return f"{dsn}?options=-csearch_path%3D{schema}" if schema else dsn


def load_settings(
    settings_yaml: Path = DEFAULT_SETTINGS_YAML,
    env_file: Path = DEFAULT_ENV_FILE,
) -> Settings:
    raw = yaml.safe_load(settings_yaml.read_text())
    return Settings(
        etl=EtlConfig(**raw["etl"]),
        recommendation=RecommendationConfig(**raw["recommendation"]),
        minio=MinioConfig(**raw["minio"]),
        postgres=PostgresConfig(**raw["postgres"]),
        igdb=IgdbConfig(**raw["igdb"]),
        secrets=Secrets(_env_file=env_file),  # type: ignore[call-arg]
    )
