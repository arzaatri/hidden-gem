# Hidden Gem

Pulls games from IGDB, lands them through a medallion (bronze/silver/gold) ETL
pipeline, and serves a small web UI where you pick up to 5 games you like and
get back niche "hidden gem" recommendations, ranked by a content-based
recommender (`ContentBasedGemFinder`) combining tag overlap and CV/NLP
embedding similarity.

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
Postgres  gold.tag_idf (IDF per genre/theme/keyword, for weighted Jaccard)
   │  new Dagster asset: embeddings/game_embeddings (Python, sentence-transformers + CLIP)
   ▼
Postgres  embeddings.game_embeddings (pgvector columns: summary/storyline/
                                       cover/screenshots embeddings)
   │
   ▼
backend: ContentBasedGemFinder scores candidates on 7 similarity signals
```

One dbt project (`dbt_project/`), running on **dbt-duckdb**, owns the whole
bronze→silver→gold transform: DuckDB reads/writes MinIO directly over S3, and
writes gold straight into Postgres via its Postgres `ATTACH` support — no
custom Python glue moving data between layers. A separate Python step
(`embeddings/`, a Dagster asset downstream of `gold.dim_games`) precomputes
CV/NLP embeddings, since that needs model inference and image downloads dbt
can't do.

Four containers: **MinIO**, **Postgres** (with the `pgvector` extension),
**Dagster** (`dagster dev`, a single process running both the webserver and
the daemon that fires schedules), **backend** (FastAPI + the static frontend).
Postgres hosts four schemas: `gold` (analytics output), `etl_state`
(incremental watermark), `dagster` (Dagster's own run/schedule history),
`embeddings` (precomputed vectors) — so all of it persists in one place.
`docker-compose.yml` uses named volumes for MinIO and Postgres and
`restart: unless-stopped`, so stopping/restarting your machine doesn't lose
data, run history, or the schedule's registration.

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
gems", and it calls `ContentBasedGemFinder` to return
`recommendation.hidden_gem_count` hidden gems ranked by similarity to your
picks. Needs `gold.dim_games` *and* `embeddings.game_embeddings` populated
(run the ETL job — including the `embeddings/game_embeddings` asset — at
least once first).

## Configuration

- **Secrets** (`.env`): IGDB creds, MinIO/Postgres creds.
- **Tunables** (`config/settings.yaml`): `etl.max_games` (capped at 100 for
  local testing — raise it for a real run), `etl.hidden_gem_rating_count_threshold`
  (the `n` behind the gold `hidden_gem` flag), bucket/schema names, the daily
  cron schedule, `recommendation.hidden_gem_count` and
  `recommendation.max_selected_games` (the web app's `N` and the 5-game cap),
  `recommendation.rating_cutoff` (hard quality filter on `aggregated_rating`;
  nulls pass), `recommendation.weights` (the 7 flat weights
  `ContentBasedGemFinder` combines its similarity signals with — must sum to 1).

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
`recommend(games: list[Game]) -> list[Game]`). `MockGemFinder` (random,
genre-overlap-only) is kept as a lightweight reference implementation but
isn't wired into the API anymore. `ContentBasedGemFinder` is what
`main.py` actually uses:

- **7 similarity signals**, each comparing a selected game to a candidate:
  IDF-weighted Jaccard over genres/themes/keywords (`gold.tag_idf` supplies
  the IDF weights), and cosine similarity over precomputed embeddings of
  summary/storyline/cover art/screenshots (`embeddings.game_embeddings`).
- **Flat weighting**: each signal gets one configured weight
  (`config/settings.yaml: recommendation.weights`, summing to 1) — no
  hierarchical grouping, so each signal's influence is directly tunable.
- **Normalization**: every signal is min-max scaled across the whole
  candidate pool for a request before combining (`backend/src/backend/content_scoring.py:normalize`)
  — raw ranges aren't comparable (tag Jaccard vs. embedding cosine similarity).
- **Missing signals renormalize weights** among whatever's available for a
  given pair (e.g. no `storyline` text) rather than scoring a missing signal
  as 0 — otherwise sparse/obscure games get penalized for lacking data, which
  is exactly backwards for a hidden-gem finder.
- **Multi-game queries**: a candidate's score is the *max* similarity across
  the up to 5 selected games, not an average — averaging across dissimilar
  picks would wash out a strong niche match.
- **Rating cutoff and `hidden_gems_only`** are hard SQL filters on the
  candidate pool (`GameRepository.get_candidate_pool`), entirely separate from
  the weighted score.

Swapping in a different/future model just means writing another `GemFinder`
subclass and pointing `main.py`'s single `gem_finder = ...` line at it —
nothing else in the API or frontend needs to change.

### Embeddings pipeline

`embeddings/` is its own uv workspace member (kept separate from `extraction`
so the heavy ML dependencies — `torch`, `transformers`, `sentence-transformers`
— don't bloat packages that don't need them). Its Dagster asset
(`embeddings/game_embeddings`) runs downstream of the dbt gold model:

- **Text**: `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim) embeds
  `summary`/`storyline`.
- **Images**: HuggingFace `transformers`' CLIP (`openai/clip-vit-base-patch32`,
  512-dim) embeds cover art and up to 3 screenshots per game (averaged into
  one vector). Images are fetched from IGDB's CDN at request time — screenshot
  URLs come from `silver/screenshots.parquet` (MinIO), since screenshots are
  silver-only detail data that never made it into `gold.dim_games`.
- **Incremental**: like the watermark for IGDB pulls, only games missing an
  embedding or whose `gold.dim_games.updated_at` is newer than their
  `embedded_at` get (re)embedded.
- `torch` is pinned to the CPU-only wheel index (`tool.uv.sources` /
  `tool.uv.index` in `embeddings/pyproject.toml`) — the default PyPI wheel
  pulls in several GB of unnecessary CUDA packages for a CPU-only container.

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

# embeddings (also needs hostnames swapped — edit config/settings.yaml temporarily,
# same as above, since it isn't Jinja-templated like dbt's profiles.yml)
uv run --package embeddings python -m embeddings
```

## Known rough edge

DuckDB's Postgres `ATTACH` write path (used for the gold table) is a less
battle-tested part of dbt-duckdb than its S3/Parquet read/write path. It only
supports `table`/`append`/`delete+insert` materializations into an attached
Postgres DB (no `merge`) — a non-issue here since gold is a small, fully
rebuilt table. If it ever proves flaky, the fallback is to materialize gold in
the local DuckDB scratch file and push it to Postgres with a small Python step
(polars' `write_database`) instead of writing through the attachment directly.
