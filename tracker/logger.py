import sqlite3
from datetime import datetime
from tracker.database import get_connection


def log_request(
    team_id: str,
    feature_name: str,
    model_used: str,
    tokens_input: int,
    tokens_output: int,
    cost: float,
    latency_ms: float,
    routing_reason: str,
    tokens_saved: int = 0,
    percent_saved: float = 0.0,
    original_prompt: str = "",
    optimized_prompt: str = ""
) -> None:
    """
    Write one row to the requests table for every LLM call.

    Called AFTER Claude responds successfully. If logging fails,
    we print a warning but do NOT crash the request — the user
    already got their answer, logging is secondary.

    Args:
        team_id          : Which team made this request.
        feature_name     : Which feature triggered this request.
        model_used       : Which Claude model was used.
        tokens_input     : Tokens in the prompt sent to Claude.
        tokens_output    : Tokens in Claude's response.
        cost             : Total cost in USD.
        latency_ms       : Response time in milliseconds.
        routing_reason   : Why this model was chosen.
        tokens_saved     : Tokens removed by the optimizer.
        percent_saved    : Percentage of tokens saved.
        original_prompt  : The raw prompt before optimization.
        optimized_prompt : The cleaned prompt sent to Claude.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO requests (
                timestamp,
                team_id,
                feature_name,
                model_used,
                tokens_input,
                tokens_output,
                cost,
                latency_ms,
                routing_reason,
                tokens_saved,
                percent_saved,
                original_prompt,
                optimized_prompt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            team_id,
            feature_name,
            model_used,
            tokens_input,
            tokens_output,
            cost,
            latency_ms,
            routing_reason,
            tokens_saved,
            percent_saved,
            original_prompt,
            optimized_prompt
        ))
        conn.commit()
    except Exception as e:
        # Log the error but do not crash the app
        print(f"⚠️  Warning: Failed to log request to database: {e}")
    finally:
        conn.close()


def get_team_spend(team_id: str) -> dict:
    """
    Return how much a team has spent today and this month.

    Used by the budget checker to decide whether to warn or block.

    How it works:
        - "today" means from midnight UTC today until now
        - "this month" means from the 1st of the current month until now
        - We SUM the cost column filtered by team_id and date range

    Args:
        team_id: The team to check.

    Returns:
        dict: {
            "daily_spend"  : float (total cost today in USD),
            "monthly_spend": float (total cost this month in USD)
        }
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.utcnow()

        # Today's date as a string prefix e.g. "2026-06-26"
        today_prefix = now.strftime("%Y-%m-%d")

        # This month's prefix e.g. "2026-06"
        month_prefix = now.strftime("%Y-%m")

        # SUM all costs for this team today
        # The timestamp column looks like "2026-06-26T14:32:11.123456"
        # LIKE "2026-06-26%" matches any timestamp from today
        cursor.execute("""
            SELECT COALESCE(SUM(cost), 0) as total
            FROM requests
            WHERE team_id = ?
            AND timestamp LIKE ?
        """, (team_id, f"{today_prefix}%"))
        daily_spend = cursor.fetchone()["total"]

        # SUM all costs for this team this month
        cursor.execute("""
            SELECT COALESCE(SUM(cost), 0) as total
            FROM requests
            WHERE team_id = ?
            AND timestamp LIKE ?
        """, (team_id, f"{month_prefix}%"))
        monthly_spend = cursor.fetchone()["total"]

        return {
            "daily_spend": round(daily_spend, 6),
            "monthly_spend": round(monthly_spend, 6)
        }

    finally:
        conn.close()


def get_all_requests(limit: int = 100) -> list:
    """
    Return the most recent requests from the database.

    Used by the dashboard to display request history.

    Args:
        limit: Maximum number of rows to return. Default 100.

    Returns:
        list: List of dicts, one per request, newest first.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT *
            FROM requests
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        # Convert each Row object to a plain dict
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_spend_by_team() -> list:
    """
    Return total spend grouped by team.

    Used by the dashboard for the team cost breakdown chart.

    Returns:
        list: List of dicts with team_id and total_cost, sorted by cost.

    Example return value:
        [
            {"team_id": "engineering", "total_cost": 0.0042},
            {"team_id": "marketing",   "total_cost": 0.0018},
        ]
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                team_id,
                ROUND(SUM(cost), 6) as total_cost,
                COUNT(*) as request_count
            FROM requests
            GROUP BY team_id
            ORDER BY total_cost DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_spend_by_model() -> list:
    """
    Return total spend grouped by model.

    Used by the dashboard for the model usage breakdown chart.

    Returns:
        list: List of dicts with model_used and total_cost.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                model_used,
                ROUND(SUM(cost), 6) as total_cost,
                COUNT(*) as request_count
            FROM requests
            GROUP BY model_used
            ORDER BY total_cost DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()