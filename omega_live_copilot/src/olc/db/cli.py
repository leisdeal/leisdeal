"""`olc-init-db` — create the SQLite DB and schema from config."""
from __future__ import annotations

import argparse

from ..config import Config
from .database import Database


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Initialize the Omega Live Copilot SQLite DB.")
    ap.add_argument("--config", default=None, help="Path to default.yaml")
    ap.add_argument("--db", default=None, help="Override storage.sqlite_path")
    args = ap.parse_args(argv)

    cfg = Config.load(args.config)
    db_path = args.db or cfg.resolve_path("storage.sqlite_path")
    db = Database(db_path)
    db.init_schema()
    print(f"[olc] DB initialized at {db.path}")
    print(f"[olc] sqlite-vec loaded: {db.vec_loaded} (FAQ vector search is Phase 3)")
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
