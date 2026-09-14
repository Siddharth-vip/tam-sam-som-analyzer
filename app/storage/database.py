import os
from pathlib import Path
import sqlite3
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)


def get_db_path(custom_path: Optional[str] = None) -> str:
    """Resolve the SQLite database filepath, creating parent directories if needed."""
    path_str = custom_path or getattr(settings, "DATABASE_PATH", "data/market_analyses.db")
    db_path = Path(path_str)
    if not db_path.is_absolute():
        # Relative to workspace root
        db_path = Path(os.getcwd()) / db_path
    
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return str(db_path)


def get_db_connection(custom_path: Optional[str] = None) -> sqlite3.Connection:
    """Create and configure a SQLite connection with row factories and WAL mode."""
    db_file = get_db_path(custom_path)
    conn = sqlite3.connect(db_file, timeout=15.0)
    conn.row_factory = sqlite3.Row
    # Configure WAL mode for concurrency and speed
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
    except Exception as pragma_err:
        logger.debug("Non-critical pragma configuration warning: %s", pragma_err)
    return conn


def init_db(custom_path: Optional[str] = None) -> None:
    """Initialize database tables and indexes if they do not already exist."""
    conn = get_db_connection(custom_path)
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analyses (
                    analysis_id TEXT PRIMARY KEY,
                    business_idea TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    business_analysis TEXT,
                    evidence_summary TEXT,
                    discovered_sources TEXT,
                    fetched_sources TEXT,
                    extracted_candidates TEXT,
                    validation_results TEXT,
                    triangulation_result TEXT,
                    calculation_report TEXT,
                    tam TEXT,
                    sam TEXT,
                    som TEXT,
                    competitors TEXT,
                    assumptions TEXT,
                    warnings TEXT,
                    errors TEXT,
                    final_result TEXT NOT NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at DESC);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_analyses_status ON analyses(status);"
            )
        logger.info("Market analysis database initialized successfully at %s", get_db_path(custom_path))
    finally:
        conn.close()
