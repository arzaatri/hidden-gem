"""Tracks the last-synced IGDB `updated_at` watermark in Postgres.

Lives outside dbt since it's pipeline metadata (state), not analytical data.
"""

from __future__ import annotations

from datetime import datetime, timezone

import psycopg

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

_BOOTSTRAP_SQL = """
CREATE SCHEMA IF NOT EXISTS etl_state;
CREATE TABLE IF NOT EXISTS etl_state.sync_watermark (
    source text PRIMARY KEY,
    last_updated_at timestamptz NOT NULL,
    last_run_at timestamptz NOT NULL
);
"""


def ensure_watermark_table(dsn: str) -> None:
    with psycopg.connect(dsn) as conn:
        conn.execute(_BOOTSTRAP_SQL)


def get_watermark(dsn: str, source: str = "igdb") -> datetime:
    """Returns the last-synced `updated_at`, or the epoch if never synced."""
    with psycopg.connect(dsn) as conn:
        row = conn.execute(
            "SELECT last_updated_at FROM etl_state.sync_watermark WHERE source = %s",
            (source,),
        ).fetchone()
    return row[0] if row else _EPOCH


def set_watermark(dsn: str, last_updated_at: datetime, source: str = "igdb") -> None:
    with psycopg.connect(dsn) as conn:
        conn.execute(
            """
            INSERT INTO etl_state.sync_watermark (source, last_updated_at, last_run_at)
            VALUES (%s, %s, now())
            ON CONFLICT (source) DO UPDATE
                SET last_updated_at = EXCLUDED.last_updated_at,
                    last_run_at = EXCLUDED.last_run_at
            """,
            (source, last_updated_at),
        )
