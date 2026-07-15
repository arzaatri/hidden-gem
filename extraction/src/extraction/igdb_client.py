"""IGDB /games client: builds Apicalypse queries and paginates through results."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import requests

from config.settings import IgdbConfig
from extraction.igdb_auth import IgdbTokenProvider

# "id" isn't in the user-facing field list but is required to page deterministically
# (sort id asc) and to give every bronze record a stable primary key.
_PAGINATION_FIELD = "id"


def _with_all_fields(game: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    """Fills in `None` for any requested field IGDB omitted from this record.

    IGDB drops a field from the response entirely when it has no value,
    rather than returning it as null. That's fine for a single record, but
    it means bronze files can have inconsistent keys across games — filling
    them in here keeps every bronze record's schema identical and complete.
    """
    base_field_names = {field.split(".")[0] for field in fields}
    return {name: game.get(name) for name in base_field_names}


class IgdbClient:
    def __init__(self, igdb: IgdbConfig, token_provider: IgdbTokenProvider) -> None:
        self._igdb = igdb
        self._token_provider = token_provider
        self._min_seconds_between_requests = 1.0 / igdb.requests_per_second
        self._last_request_at: float = 0.0

    def fetch_games(self, updated_after: datetime, max_games: int) -> list[dict[str, Any]]:
        """Pulls up to `max_games` games updated after `updated_after`."""
        fields = [_PAGINATION_FIELD, *self._igdb.fields]
        collected: list[dict[str, Any]] = []
        offset = 0
        page_size = min(self._igdb.page_size, max_games)

        while len(collected) < max_games:
            remaining = max_games - len(collected)
            limit = min(page_size, remaining)
            query = (
                f"fields {','.join(fields)};\n"
                f"where updated_at > {int(updated_after.timestamp())};\n"
                f"sort id asc;\n"
                f"limit {limit};\n"
                f"offset {offset};"
            )
            page = self.raw_query("games", query)
            if not page:
                break
            collected.extend(_with_all_fields(game, fields) for game in page)
            offset += len(page)
            if len(page) < limit:
                break  # last page was partial: no more results

        return collected

    def raw_query(self, endpoint: str, query: str) -> list[dict[str, Any]]:
        """Runs an arbitrary Apicalypse query against any IGDB endpoint.

        `fetch_games` covers the production pull; this is the escape hatch
        for ad hoc exploration (other endpoints, other fields).
        """
        self._respect_rate_limit()
        token = self._token_provider.get_token()
        response = requests.post(
            f"{self._igdb.api_base_url}/{endpoint}",
            headers={
                "Client-ID": self._token_provider.client_id,
                "Authorization": f"Bearer {token}",
            },
            data=query,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def _respect_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        wait = self._min_seconds_between_requests - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()
