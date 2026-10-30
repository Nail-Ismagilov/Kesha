"""HTTP access. One shared session (keep-alive, connection pool) with timeouts."""
from dataclasses import dataclass
from typing import Optional

import requests
from requests.adapters import HTTPAdapter

TIMEOUT = (5, 30)  # (connect, read) seconds
POOL_SIZE = 16     # enough for the default number of worker threads

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "dogwatch/0.1"})
for _prefix in ("http://", "https://"):
    SESSION.mount(_prefix, HTTPAdapter(pool_connections=POOL_SIZE, pool_maxsize=POOL_SIZE))


@dataclass
class Fetched:
    status: int                       # 200, or 304 = "not modified, use your cache"
    text: str = ""
    etag: Optional[str] = None
    last_modified: Optional[str] = None


def fetch_page(url, etag=None, last_modified=None):
    """GET a page; sends validators so an unchanged page costs only a 304."""
    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    resp = SESSION.get(url, headers=headers, timeout=TIMEOUT)
    if resp.status_code == 304:
        return Fetched(304, "", etag, last_modified)
    resp.raise_for_status()
    return Fetched(200, resp.text, resp.headers.get("ETag"), resp.headers.get("Last-Modified"))


def head_size(url):
    """Content-Length of `url` in bytes via HEAD, or None if unknown."""
    try:
        resp = SESSION.head(url, allow_redirects=True, timeout=TIMEOUT)
        value = resp.headers.get("Content-Length", "")
        return int(value) if value.isdigit() else None
    except Exception:
        return None


def get_bytes(url):
    """Download an image. Raises if the response is not an image."""
    resp = SESSION.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    if not resp.headers.get("Content-Type", "").startswith("image/"):
        raise ValueError("not an image response")
    return resp.content
