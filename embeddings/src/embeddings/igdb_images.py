"""Builds IGDB CDN image URLs from a cover/screenshot `image_id`.

Python-side equivalent of the `igdbCoverUrl` helper in backend/static/app.js —
duplicated rather than shared since one is Python and the other browser JS.
"""

from __future__ import annotations

_BASE_URL = "https://images.igdb.com/igdb/image/upload"


def igdb_image_url(image_id: str, size: str) -> str:
    return f"{_BASE_URL}/t_{size}/{image_id}.jpg"
