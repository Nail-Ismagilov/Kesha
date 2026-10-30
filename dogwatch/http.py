"""HTTP access. One shared session (keep-alive) with sane timeouts."""
import requests

TIMEOUT = (5, 30)  # (connect, read) seconds
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "dogwatch/0.1"})


def get_html(url):
    resp = SESSION.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text
