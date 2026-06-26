from tracker.database import get_connection
from tracker.logger import get_team_spend


def get_team_budget(team_id: str) -> dict:
    """
    Fetch the budget limits for a specific team from the database.

    If the team has no budget row, return generous defaults.
    This means unknown teams are not blocked — they just get
    high default limits. You can tighten this in production.

    Args:
        team_id: The team to look up.

    Returns:
        dict: {
            "daily_limit"  : float,
            "monthly_limit": float
        }
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT daily_limit, monthly_limit
            FROM budgets
            WHERE team_id = ?
        """, (team_id,))

        row = cursor.fetchone()

        if row:
            return {
                "daily_limit": row["daily_limit"],
                "monthly_limit": row["monthly_limit"]
            }
        else:
            # Team not found in budgets table — use generous defaults
            return {
                "daily_limit": 5.00,
                "monthly_limit": 100.00
            }
    finally:
        conn.close()


def check_budget(team_id: str, priority: str) -> dict:
    """
    Check whether a team is within their budget before making an LLM call.

    This runs BEFORE calling Claude. If the team is blocked,
    we return an error immediately and never touch the LLM.

    Three possible statuses:

        ALLOWED  → Spend is under 80% of limit. Proceed normally.
        WARNING  → Spend is 80-99% of limit. Proceed but warn the caller.
        BLOCKED  → Spend is at or over 100% of limit.
                   Low and medium priority requests are blocked.
                   High priority requests still go through
                   (some things cannot wait for a budget reset).

    Why allow high priority through even when blocked?
    Because if a critical system needs an answer, stopping it
    due to budget is worse than the cost of one extra request.

    Args:
        team_id : The team making the request.
        priority: "low", "medium", or "high".

    Returns:
        dict: {
            "status"         : "allowed", "warning", or "blocked",
            "message"        : str (human-readable explanation),
            "daily_spend"    : float,
            "monthly_spend"  : float,
            "daily_limit"    : float,
            "monthly_limit"  : float,
            "daily_percent"  : float (% of daily limit used),
            "monthly_percent": float (% of monthly limit used)
        }
    """

    # Get this team's limits and current spend
    budget = get_team_budget(team_id)
    spend = get_team_spend(team_id)

    daily_limit = budget["daily_limit"]
    monthly_limit = budget["monthly_limit"]
    daily_spend = spend["daily_spend"]
    monthly_spend = spend["monthly_spend"]

    # Calculate what percentage of each limit has been used
    # We check both daily and monthly — whichever is worse wins
    daily_percent = (daily_spend / daily_limit * 100) if daily_limit > 0 else 0
    monthly_percent = (monthly_spend / monthly_limit * 100) if monthly_limit > 0 else 0

    # The binding constraint is whichever limit is more exhausted
    worst_percent = max(daily_percent, monthly_percent)
    binding = "daily" if daily_percent >= monthly_percent else "monthly"
    binding_spend = daily_spend if binding == "daily" else monthly_spend
    binding_limit = daily_limit if binding == "daily" else monthly_limit

    # Base response object (filled in by each branch below)
    result = {
        "daily_spend": daily_spend,
        "monthly_spend": monthly_spend,
        "daily_limit": daily_limit,
        "monthly_limit": monthly_limit,
        "daily_percent": round(daily_percent, 1),
        "monthly_percent": round(monthly_percent, 1)
    }

    # -------------------------------------------------------------------
    # BLOCKED: at or over 100% of limit
    # -------------------------------------------------------------------
    if worst_percent >= 100:
        if priority == "high":
            # High priority punches through even when blocked
            result["status"] = "warning"
            result["message"] = (
                f"⚠️  Team '{team_id}' has exceeded their {binding} budget "
                f"(${binding_spend:.4f} / ${binding_limit:.2f}). "
                f"Request allowed because priority is 'high'."
            )
        else:
            result["status"] = "blocked"
            result["message"] = (
                f"🚫 Team '{team_id}' has reached their {binding} budget limit "
                f"(${binding_spend:.4f} / ${binding_limit:.2f}). "
                f"Request blocked. "
                f"Set priority='high' to override, or wait for budget reset."
            )
        return result

    # -------------------------------------------------------------------
    # WARNING: between 80% and 100%
    # -------------------------------------------------------------------
    if worst_percent >= 80:
        result["status"] = "warning"
        result["message"] = (
            f"⚠️  Team '{team_id}' has used {worst_percent:.1f}% "
            f"of their {binding} budget "
            f"(${binding_spend:.4f} / ${binding_limit:.2f}). "
            f"Approaching limit."
        )
        return result

    # -------------------------------------------------------------------
    # ALLOWED: under 80%
    # -------------------------------------------------------------------
    result["status"] = "allowed"
    result["message"] = (
        f"✅ Team '{team_id}' is within budget "
        f"(daily: {daily_percent:.1f}%, monthly: {monthly_percent:.1f}%)."
    )
    return result