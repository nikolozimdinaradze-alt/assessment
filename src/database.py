import logging
import sqlite3
import sys
from pathlib import Path
from typing import Generator

from src.conf import settings

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path("migrations")


def apply_migrations(connection: sqlite3.Connection) -> None:
    current_version = connection.execute("PRAGMA user_version").fetchone()[0]

    migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))

    logger.info("Current schema version: %s", current_version)

    for version, migration in enumerate(migrations, start=1):
        if version <= current_version:
            logger.info("Migration already applied: %s", migration)
            continue

        logger.info("Applying migration %s", migration.name)

        try:
            with connection:
                connection.executescript(migration.read_text())
                connection.execute(f"PRAGMA user_version = {version}")

        except Exception:
            logger.exception("Failed to apply migration %s", migration.name)
            sys.exit(1)

    logger.info("Migrations completed")


def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(settings.DB_URI, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        yield conn
    finally:
        conn.close()
