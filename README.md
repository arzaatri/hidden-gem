# Hidden Gem

Pulls games from IGDB, lands them through a medallion (bronze/silver/gold) ETL
pipeline, and serves a small web UI where you pick up to 5 games you like and
get back niche "hidden gem" recommendations. The recommendation logic itself
is still a placeholder (`MockGemFinder`) — the real recommendation model comes
later.

## Architecture

```
IGDB API (OAuth2 client-credentials)
   │  Python, invoked by a Dagster asset (extraction/)
   ▼
MinIO  hidden-game/bronze/*.json   (raw, denormalized, 1 record/game)
   │  dbt-duckdb staging + silver models (read straight from MinIO via S3/httpfs)
   ▼
MinIO  hidden-game/silver/*.parquet (normalized: games, genres, themes,
   │                                  keywords, bridge tables, screenshots)
   │  dbt-duckdb gold model (DuckDB ATTACH → Postgres)
   ▼
Postgres  gold.dim_games (hidden_gem flag, aggregated genres/themes/keywords)
```

One dbt project (`dbt_project/`), running on **dbt-duckdb**, owns the whole
bronze→silver→gold transform: DuckDB reads/writes MinIO directly over S3, and
writes gold straight into Postgres via its Postgres `ATTACH` support — no
custom Python glue moving data between layers.

Three containers: **MinIO**, **Postgres**, **Dagster** (`dagster dev`, a single
process running both the webserver and the daemon that fires schedules).
Postgres hosts three schemas: `gold` (analytics output), `etl_state`
(incremental watermark), `dagster` (Dagster's own run/schedule history) — so
all of it persists in one place. `docker-compose.yml` uses named volumes for
MinIO and Postgres and `restart: unless-stopped`, so stopping/restarting your
machine doesn't lose data, run history, or the schedule's registration.

## Running it

```bash
cp .env.example .env   # fill in IGDB_CLIENT_ID / IGDB_CLIENT_SECRET
docker compose up -d
```

Dagster UI: http://localhost:3000 — the `daily_hidden_gem_sync` job runs on a
daily cron (`config/settings.yaml: etl.schedule_cron`) and is **on by default**.
To trigger a run immediately instead of waiting for the schedule, use the UI's
"Materialize all" button, or:

```bash
docker exec hidden-gem-dagster-1 uv run dagster job launch -m orchestration.definitions -j daily_hidden_gem_sync
```

MinIO console: http://localhost:9001 (creds from `.env`).

**Web app**: http://localhost:8000 — search for up to 5 games, hit "Mine for
gems", and it calls `MockGemFinder` to return `recommendation.hidden_gem_count`
random hidden gems sharing a genre with your picks. Needs `gold.dim_games` to
already be populated (run the ETL job at least once first).

## Configuration

- **Secrets** (`.env`): IGDB creds, MinIO/Postgres creds.
- **Tunables** (`config/settings.yaml`): `etl.max_games` (capped at 100 for
  local testing — raise it for a real run), `etl.hidden_gem_rating_count_threshold`
  (the `n` behind the gold `hidden_gem` flag), bucket/schema names, the daily
  cron schedule, `recommendation.hidden_gem_count` and
  `recommendation.max_selected_games` (the web app's `N` and the 5-game cap).

Both are loaded through `config/settings.py` (a single Pydantic `Settings`
object) so there's one source of truth for both the Python extraction code and
the dbt project (passed in as `--vars`).

## Incremental refresh

`etl_state.sync_watermark` (Postgres) tracks the max IGDB `updated_at` seen so
far. Each run only pulls games updated after that watermark, and only advances
it after bronze is written successfully — a failed run just re-pulls the same
window next time. Because IGDB never returns the *same* game twice with an
older `updated_at`, but the same game *can* reappear across multiple daily
bronze files if it changes, `stg_games` (dbt) dedupes to the newest record per
game before anything reaches silver/gold.

## Recommendation logic

`backend/src/backend/gem_finder.py` defines `GemFinder` (abstract:
`recommend(games: list[Game]) -> list[Game]`) and `MockGemFinder`, which
samples random `hidden_gem` games sharing a genre with the input. Swapping in
a real model later just means writing another `GemFinder` subclass and
pointing `backend/src/backend/main.py`'s single `gem_finder = ...` line at it
— nothing else in the API or frontend needs to change.

## Local development (outside Docker)

```bash
uv sync --all-packages
```

To run a piece manually against the Dockerized MinIO/Postgres from your host
(rather than from inside the `dagster` container), override the hostnames dbt
and the extraction code otherwise resolve via Docker's internal network:

```bash
# extraction
uv run --package extraction python -m extraction   # uses config/settings.yaml as-is (container hostnames)

# dbt (needs container hostnames swapped for localhost)
MINIO_ENDPOINT=localhost:9000 POSTGRES_HOST=localhost \
  uv run --package orchestration dbt build --project-dir dbt_project --profiles-dir dbt_project
```

## Known rough edge

DuckDB's Postgres `ATTACH` write path (used for the gold table) is a less
battle-tested part of dbt-duckdb than its S3/Parquet read/write path. It only
supports `table`/`append`/`delete+insert` materializations into an attached
Postgres DB (no `merge`) — a non-issue here since gold is a small, fully
rebuilt table. If it ever proves flaky, the fallback is to materialize gold in
the local DuckDB scratch file and push it to Postgres with a small Python step
(pandas `to_sql`) instead of writing through the attachment directly.
