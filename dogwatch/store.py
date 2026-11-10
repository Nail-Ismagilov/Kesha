"""State in one SQLite file (WAL). Safe to share between worker threads."""
import json
import sqlite3
import threading
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS descriptions (
    dog_key    TEXT PRIMARY KEY,
    hash       TEXT NOT NULL,
    text       TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    changed_at TEXT
);
CREATE TABLE IF NOT EXISTS pages (
    dog_key       TEXT PRIMARY KEY,
    etag          TEXT,
    last_modified TEXT,
    description   TEXT NOT NULL,
    photo_urls    TEXT NOT NULL,
    fetched_at    TEXT NOT NULL
);
"""


def _now():
    return datetime.now().isoformat(timespec="seconds")


class Store:
    def __init__(self, path=":memory:"):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            if path != ":memory:":
                self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    # --- description baseline -------------------------------------------- #
    def get_description(self, key):
        """Return (hash, text) or None."""
        with self._lock:
            row = self._conn.execute(
                "SELECT hash, text FROM descriptions WHERE dog_key=?", (key,)).fetchone()
        return row

    def put_description(self, key, hash_, text, changed):
        now = _now()
        with self._lock:
            if self._conn.execute("SELECT 1 FROM descriptions WHERE dog_key=?",
                                  (key,)).fetchone():
                if changed:
                    self._conn.execute(
                        "UPDATE descriptions SET hash=?, text=?, checked_at=?, changed_at=? "
                        "WHERE dog_key=?", (hash_, text, now, now, key))
                else:
                    self._conn.execute(
                        "UPDATE descriptions SET checked_at=? WHERE dog_key=?", (now, key))
            else:
                self._conn.execute(
                    "INSERT INTO descriptions(dog_key, hash, text, checked_at, changed_at) "
                    "VALUES (?,?,?,?,NULL)", (key, hash_, text, now))
            self._conn.commit()

    # --- page cache (validators + parsed content, for 304 answers) --------- #
    def get_page_cache(self, key):
        """Return dict(etag, last_modified, description, photo_urls) or None."""
        with self._lock:
            row = self._conn.execute(
                "SELECT etag, last_modified, description, photo_urls FROM pages WHERE dog_key=?",
                (key,)).fetchone()
        if row is None:
            return None
        return {"etag": row[0], "last_modified": row[1], "description": row[2],
                "photo_urls": json.loads(row[3])}

    def put_page_cache(self, key, etag, last_modified, description, photo_urls):
        with self._lock:
            self._conn.execute(
                "INSERT INTO pages(dog_key, etag, last_modified, description, photo_urls, fetched_at) "
                "VALUES (?,?,?,?,?,?) ON CONFLICT(dog_key) DO UPDATE SET "
                "etag=excluded.etag, last_modified=excluded.last_modified, "
                "description=excluded.description, photo_urls=excluded.photo_urls, "
                "fetched_at=excluded.fetched_at",
                (key, etag, last_modified, description, json.dumps(photo_urls), _now()))
            self._conn.commit()

    def close(self):
        with self._lock:
            self._conn.close()
