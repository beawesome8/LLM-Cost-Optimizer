import sqlite3
import os
from datetime import datetime

# -----------------------------------------------------------------------
# DATABASE FILE PATH
#
# The database lives in the project root as "cost_optimizer.db"
# This single file contains all our tables and data.
# It is listed in .gitignore so it never gets pushed to GitHub.
# (It contains real usage data and grows over time)
# -----------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "cost_optimizer.db")


def get_connection() -> sqlite3.Connection:
    """
    Open and return a connection to the SQLite database.

    sqlite3.connect() creates the file automatically if it does
    not exist yet. So the first time this runs, it creates
    cost_optimizer.db in your project root.

    We set row_factory = sqlite3.Row so that query results
    come back as dictionary-like objects instead of plain tuples.
    This means you can write result["team_id"] instead of result[0].

    Returns:
        sqlite3.Connection: An open database connection.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database() -> None:
    """
    Create all database tables if they do not already exist.

    This runs once at server startup (called from main.py).
    If the tables already exist, nothing changes — safe to run
    multiple times.

    Tables created:
        requests : One row per LLM request. Full audit trail.
        budgets  : One row per team. Daily and monthly limits.

    SQL keyword explanation:
        CREATE TABLE IF NOT EXISTS → only create if not already there
        TEXT    → stores any string
        REAL    → stores decimal numbers (for cost, latency)
        INTEGER → stores whole numbers (for token counts)
        PRIMARY KEY AUTOINCREMENT → id is set automatically, always unique
    """
    conn = get_connection()

    try:
        cursor = conn.cursor()

        # -----------------------------------------------------------
        # TABLE 1: requests
        # Every single LLM call gets logged here.
        # This is our full audit trail — queryable forever.
        # -----------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp       TEXT    NOT NULL,
                team_id         TEXT    NOT NULL,
                feature_name    TEXT    NOT NULL,
                model_used      TEXT    NOT NULL,
                tokens_input    INTEGER NOT NULL,
                tokens_output   INTEGER NOT NULL,
                cost            REAL    NOT NULL,
                latency_ms      REAL    NOT NULL,
                routing_reason  TEXT    NOT NULL,
                tokens_saved    INTEGER NOT NULL DEFAULT 0,
                percent_saved   REAL    NOT NULL DEFAULT 0.0,
                original_prompt TEXT,
                optimized_prompt TEXT
            )
        """)

        # -----------------------------------------------------------
        # TABLE 2: budgets
        # One row per team. Defines their spending limits.
        # If a team has no row here, they have no budget limit.
        # -----------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                team_id         TEXT PRIMARY KEY,
                daily_limit     REAL NOT NULL DEFAULT 1.00,
                monthly_limit   REAL NOT NULL DEFAULT 20.00
            )
        """)

        # -----------------------------------------------------------
        # SEED DEFAULT BUDGETS
        # Insert some example teams with budget limits.
        # INSERT OR IGNORE means: if this team_id already exists,
        # do nothing. So re-running this is always safe.
        # -----------------------------------------------------------
        default_budgets = [
            ("marketing",   1.00,  20.00),
            ("sales",       0.50,  10.00),
            ("engineering", 2.00,  50.00),
            ("strategy",    1.50,  30.00),
            ("content",     0.75,  15.00),
        ]

        cursor.executemany("""
            INSERT OR IGNORE INTO budgets (team_id, daily_limit, monthly_limit)
            VALUES (?, ?, ?)
        """, default_budgets)

        # Save all changes to the file
        conn.commit()
        print("✅ Database initialized successfully.")

    finally:
        # Always close the connection — even if an error occurred
        conn.close()