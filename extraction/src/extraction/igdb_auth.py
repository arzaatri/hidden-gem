"""Twitch OAuth2 client-credentials flow used to authenticate against IGDB."""

from __future__ import annotations

import time

import requests
from pydantic import BaseModel

from config.settings import IgdbConfig, Secrets


class AccessToken(BaseModel):
    token: str
    expires_at: float  # unix timestamp


class IgdbTokenProvider:
    """Fetches and caches an IGDB access token for the process lifetime.

    IGDB tokens are valid for ~months, so an in-memory cache with an
    expiry check is enough — no need to persist it anywhere.
    """

    def __init__(self, igdb: IgdbConfig, secrets: Secrets) -> None:
        self._igdb = igdb
        self._secrets = secrets
        self._cached: AccessToken | None = None

    @property
    def client_id(self) -> str:
        return self._secrets.igdb_client_id

    def get_token(self) -> str:
        if self._cached is None or time.time() >= self._cached.expires_at:
            self._cached = self._fetch_token()
        return self._cached.token

    def _fetch_token(self) -> AccessToken:
        response = requests.post(
            self._igdb.auth_url,
            params={
                "client_id": self._secrets.igdb_client_id,
                "client_secret": self._secrets.igdb_client_secret,
                "grant_type": "client_credentials",
            },
            timeout=10,
        )
        response.raise_for_status()
        body = response.json()
        return AccessToken(
            token=body["access_token"],
            expires_at=time.time() + body["expires_in"],
        )
