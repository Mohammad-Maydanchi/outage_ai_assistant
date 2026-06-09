"""SQLite connection helper for the POC.

Phase 0 only needs to prove we can open a connection. Table creation comes
in Phase 1 with the data models.
"""

import sqlite3
from pathlib import Path

from app.config import settings


def _sqlite_path() -> str:
    """Turn a sqlite:/// URL into a filesystem path."""
    url = settings.database_url
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "", 1)
    return url


def get_connection() -> sqlite3.Connection:
    """Open a SQLite connection (creates the file if missing)."""
    path = _sqlite_path()
    # Ensure the parent directory exists for nested paths.
    parent = Path(path).parent
    if str(parent) not in ("", "."):
        parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def check_connection() -> bool:
    """Return True if the database answers a trivial query."""
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
        return True
    except sqlite3.Error:
        return False
