"""SQLite access. Local-first (PRD §12). sqlite-vec loaded opportunistically —
its absence never blocks Phase 1 (speaker monitor uses in-memory similarity).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def _try_load_sqlite_vec(conn: sqlite3.Connection) -> bool:
    """Load the sqlite-vec extension if available. Returns success flag.

    FAQ vector search (Phase 3) needs this; the speaker monitor does not, so a
    False here is logged by callers but is not fatal.
    """
    try:
        import sqlite_vec  # type: ignore

        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return True
    except Exception:
        return False


def connect(db_path: str | Path, *, load_vec: bool = True) -> sqlite3.Connection:
    """Open a connection. Note: sqlite3.Connection does not accept arbitrary
    attributes, so vec-load status is tracked by :class:`Database`, not on the
    connection object. Use :func:`Database` if you need that flag."""
    path = Path(db_path)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if load_vec:
        _try_load_sqlite_vec(conn)
    return conn


class Database:
    """Owns the connection and schema init."""

    def __init__(self, db_path: str | Path, *, load_vec: bool = True):
        self.path = str(db_path)
        path = Path(db_path)
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.vec_loaded: bool = _try_load_sqlite_vec(self.conn) if load_vec else False

    def init_schema(self) -> None:
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as fh:
            self.conn.executescript(fh.read())
        self._init_vec_tables()
        self.conn.commit()

    def _init_vec_tables(self) -> None:
        """Create FAQ vector table only if the extension is present (Phase 3)."""
        if not self.vec_loaded:
            return
        # dim is configurable; default matches config storage.vector.dim.
        self.conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS faq_vec USING vec0("
            "  faq_id INTEGER PRIMARY KEY, embedding FLOAT[1024])"
        )

    def execute(self, sql: str, params=()):
        return self.conn.execute(sql, params)

    def commit(self) -> None:
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
