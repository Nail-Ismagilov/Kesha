"""State in one SQLite file (WAL). Safe to share between worker threads."""
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

    def close(self):
        with self._lock:
            self._conn.close()
