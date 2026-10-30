"""HTTP access. One shared session (keep-alive) with sane timeouts."""
import requests

TIMEOUT = (5, 30)  # (connect, read) seconds
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "dogwatch/0.1"})


def get_html(url):
    resp = SESSION.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text


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
