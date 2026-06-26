import streamlit as st
import sqlite3
import os
import sys
import pandas as pd

# -----------------------------------------------------------------------
# PATH FIX
#
# When Streamlit runs this file, it does not automatically know
# where the rest of your project is. We add the project root to
# Python's search path so imports like "from tracker.logger import..."
# work correctly.
#
# os.path.dirname(__file__)  → the dashboard/ folder
# os.path.join(..., "..")    → one level up = project root
# os.path.abspath(...)       → convert to absolute path
# sys.path.insert(0, ...)    → add to front of Python's search path
# -----------------------------------------------------------------------
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tracker.logger import (
    get_all_requests,
    get_spend_by_team,
    get_spend_by_model
)
from tracker.database import get_connection
from models.registry import registry


# -----------------------------------------------------------------------
# PAGE CONFIGURATION
#
# Must be the FIRST Streamlit call in the file.
# Sets the browser tab title, icon, and layout.
# "wide" layout uses the full browser width instead of a narrow column.
# -----------------------------------------------------------------------
st.set_page_config(
    page_title="LLM Cost Optimizer",
    page_icon="💰",
    layout="wide"
)


# -----------------------------------------------------------------------
# HELPER FUNCTIONS
# These query the database for specific numbers the dashboard needs.
# -----------------------------------------------------------------------

def get_total_spend() -> float:
    """Return total spend across all teams and all time."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(SUM(cost), 0) FROM requests")
        return round(cursor.fetchone()[0], 6)
    finally:
        conn.close()


def get_total_requests() -> int:
    """Return total number of requests logged."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM requests")
        return cursor.fetchone()[0]
    finally:
        conn.close()


def get_total_tokens_saved() -> int:
    """Return total tokens saved by the prompt optimizer."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(SUM(tokens_saved), 0) FROM requests")
        return cursor.fetchone()[0]
    finally:
        conn.close()


def get_baseline_spend() -> float:
    """
    Calculate what the total spend WOULD have been if every request
    was sent to Claude Opus (the most expensive model).

    This is the key savings metric for the portfolio case study.

    Formula:
        baseline_cost = (tokens_input / 1000 * opus_input_price)
                      + (tokens_output / 1000 * opus_output_price)

    We compare this to actual_spend to show the savings.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT tokens_input, tokens_output FROM requests")
        rows = cursor.fetchall()

        # Opus pricing from our registry
        opus = registry.get_model("claude-opus-4-6")
        opus_input_price = opus.input_cost_per_1k_tokens
        opus_output_price = opus.output_cost_per_1k_tokens

        baseline = 0.0
        for row in rows:
            tokens_in = row[0]
            tokens_out = row[1]
            cost = (
                (tokens_in / 1000 * opus_input_price) +
                (tokens_out / 1000 * opus_output_price)
            )
            baseline += cost

        return round(baseline, 6)

    finally:
        conn.close()


# -----------------------------------------------------------------------
# SIDEBAR
#
# The sidebar is the panel on the left side of the screen.
# We use it for navigation and for a quick budget overview.
# -----------------------------------------------------------------------
with st.sidebar:
    st.title("💰 LLM Cost Optimizer")
    st.markdown("---")

    # Navigation
    page = st.radio(
        "Navigate",
        ["📊 Overview", "👥 Team Spend", "🤖 Model Usage", "📋 Request Log", "💡 Savings Report"]
    )

    st.markdown("---")
    st.caption("Data refreshes on page load.")
    st.caption("Built with FastAPI + SQLite + Streamlit")


# -----------------------------------------------------------------------
# PAGE: OVERVIEW
# -----------------------------------------------------------------------
if page == "📊 Overview":

    st.title("📊 LLM Cost Optimizer — Dashboard")
    st.markdown("Real-time visibility into LLM spend, routing decisions, and token savings.")
    st.markdown("---")

    # ---------------------------------------------------------------
    # ROW 1: HEADLINE METRICS
    # st.columns(4) creates 4 equal-width columns side by side.
    # We put one metric in each column.
    # ---------------------------------------------------------------
    total_spend = get_total_spend()
    total_requests = get_total_requests()
    total_tokens_saved = get_total_tokens_saved()
    baseline_spend = get_baseline_spend()
    savings = round(baseline_spend - total_spend, 6)
    savings_percent = (
        round((savings / baseline_spend) * 100, 1)
        if baseline_spend > 0 else 0
    )
    avg_cost = round(total_spend / total_requests, 6) if total_requests > 0 else 0

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="💵 Total Spend",
            value=f"${total_spend:.6f}",
            help="Total USD spent across all teams and requests"
        )

    with col2:
        st.metric(
            label="📨 Total Requests",
            value=f"{total_requests:,}",
            help="Total number of LLM requests processed"
        )

    with col3:
        st.metric(
            label="🪙 Avg Cost per Request",
            value=f"${avg_cost:.6f}",
            help="Average USD cost per request"
        )

    with col4:
        st.metric(
            label="✂️ Tokens Saved",
            value=f"{total_tokens_saved:,}",
            help="Total tokens removed by the prompt optimizer"
        )

    st.markdown("---")

    # ---------------------------------------------------------------
    # ROW 2: CHARTS SIDE BY SIDE
    # ---------------------------------------------------------------
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("💸 Spend by Team")
        team_data = get_spend_by_team()
        if team_data:
            # Convert list of dicts to a pandas DataFrame
            # A DataFrame is like an Excel table in Python
            df_teams = pd.DataFrame(team_data)
            df_teams = df_teams.set_index("team_id")
            st.bar_chart(df_teams["total_cost"])
        else:
            st.info("No data yet. Send some requests first.")

    with col_right:
        st.subheader("🤖 Spend by Model")
        model_data = get_spend_by_model()
        if model_data:
            df_models = pd.DataFrame(model_data)
            df_models = df_models.set_index("model_used")
            st.bar_chart(df_models["total_cost"])
        else:
            st.info("No data yet. Send some requests first.")

    st.markdown("---")

    # ---------------------------------------------------------------
    # ROW 3: SAVINGS SUMMARY
    # ---------------------------------------------------------------
    st.subheader("💡 Savings vs Baseline")
    st.markdown(
        "**Baseline** = what it would cost if every request went to Claude Opus. "
        "**Actual** = what you really paid with smart routing."
    )

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.metric(
            label="📈 Baseline Cost (all Opus)",
            value=f"${baseline_spend:.6f}"
        )

    with col_b:
        st.metric(
            label="✅ Actual Cost",
            value=f"${total_spend:.6f}"
        )

    with col_c:
        st.metric(
            label="💰 Total Saved",
            value=f"${savings:.6f}",
            delta=f"{savings_percent}% cheaper than baseline",
            delta_color="normal"
        )


# -----------------------------------------------------------------------
# PAGE: TEAM SPEND
# -----------------------------------------------------------------------
elif page == "👥 Team Spend":

    st.title("👥 Team Spend Breakdown")
    st.markdown("See how much each team is spending and how close they are to their budget.")
    st.markdown("---")

    team_data = get_spend_by_team()

    if not team_data:
        st.info("No requests logged yet.")
    else:
        # Show one row per team with spend and request count
        df = pd.DataFrame(team_data)
        df.columns = ["Team", "Total Cost (USD)", "Request Count"]
        df["Avg Cost per Request"] = (
            df["Total Cost (USD)"] / df["Request Count"]
        ).round(6)
        st.dataframe(df, use_container_width=True)

        st.markdown("---")
        st.subheader("Budget Status")

        # Show budget usage per team
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM budgets")
        budgets = [dict(row) for row in cursor.fetchall()]
        conn.close()

        from tracker.logger import get_team_spend

        for b in budgets:
            tid = b["team_id"]
            spend = get_team_spend(tid)

            daily_pct = (
                spend["daily_spend"] / b["daily_limit"] * 100
                if b["daily_limit"] > 0 else 0
            )
            monthly_pct = (
                spend["monthly_spend"] / b["monthly_limit"] * 100
                if b["monthly_limit"] > 0 else 0
            )

            # Color the progress bar based on how full it is
            status_color = (
                "🔴" if daily_pct >= 100
                else "🟡" if daily_pct >= 80
                else "🟢"
            )

            with st.expander(f"{status_color} {tid}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Daily:** ${spend['daily_spend']:.6f} / ${b['daily_limit']:.2f}")
                    st.progress(min(daily_pct / 100, 1.0))
                    st.caption(f"{daily_pct:.1f}% used")
                with c2:
                    st.markdown(f"**Monthly:** ${spend['monthly_spend']:.6f} / ${b['monthly_limit']:.2f}")
                    st.progress(min(monthly_pct / 100, 1.0))
                    st.caption(f"{monthly_pct:.1f}% used")


# -----------------------------------------------------------------------
# PAGE: MODEL USAGE
# -----------------------------------------------------------------------
elif page == "🤖 Model Usage":

    st.title("🤖 Model Usage Breakdown")
    st.markdown("See which models are being used and how much each one costs.")
    st.markdown("---")

    model_data = get_spend_by_model()

    if not model_data:
        st.info("No requests logged yet.")
    else:
        df = pd.DataFrame(model_data)
        df.columns = ["Model", "Total Cost (USD)", "Request Count"]
        df["Avg Cost per Request"] = (
            df["Total Cost (USD)"] / df["Request Count"]
        ).round(6)

        st.dataframe(df, use_container_width=True)
        st.markdown("---")

        st.subheader("Cost by Model")
        df_chart = df.set_index("Model")
        st.bar_chart(df_chart["Total Cost (USD)"])

        st.markdown("---")
        st.subheader("Model Pricing Reference")

        pricing_data = []
        for name, model in registry.list_all().items():
            pricing_data.append({
                "Model": name,
                "Tier": model.quality_tier,
                "Input (per 1K tokens)": f"${model.input_cost_per_1k_tokens}",
                "Output (per 1K tokens)": f"${model.output_cost_per_1k_tokens}",
                "Description": model.description
            })

        st.dataframe(pd.DataFrame(pricing_data), use_container_width=True)


# -----------------------------------------------------------------------
# PAGE: REQUEST LOG
# -----------------------------------------------------------------------
elif page == "📋 Request Log":

    st.title("📋 Full Request Log")
    st.markdown("Every LLM request logged with full routing and cost detail.")
    st.markdown("---")

    requests = get_all_requests(limit=200)

    if not requests:
        st.info("No requests logged yet.")
    else:
        df = pd.DataFrame(requests)

        # Show only the most useful columns
        display_cols = [
            "timestamp", "team_id", "feature_name",
            "model_used", "tokens_input", "tokens_output",
            "cost", "latency_ms", "tokens_saved", "routing_reason"
        ]

        # Only show columns that exist in the dataframe
        display_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True)

        st.markdown("---")
        st.caption(f"Showing {len(df)} most recent requests.")


# -----------------------------------------------------------------------
# PAGE: SAVINGS REPORT
# -----------------------------------------------------------------------
elif page == "💡 Savings Report":

    st.title("💡 Savings Report")
    st.markdown(
        "This is your **portfolio case study headline metric.** "
        "It shows exactly how much the optimizer saved vs sending "
        "everything to the most expensive model."
    )
    st.markdown("---")

    total_spend = get_total_spend()
    total_requests = get_total_requests()
    total_tokens_saved = get_total_tokens_saved()
    baseline_spend = get_baseline_spend()
    savings = round(baseline_spend - total_spend, 6)
    savings_percent = (
        round((savings / baseline_spend) * 100, 1)
        if baseline_spend > 0 else 0
    )

    # ---------------------------------------------------------------
    # HEADLINE METRIC — This is what you say in interviews
    # ---------------------------------------------------------------
    st.markdown("### 🏆 Headline Result")
    st.success(
        f"**Reduced LLM spend by {savings_percent}%** across "
        f"{total_requests:,} requests by combining prompt optimization "
        f"and complexity-based model routing. "
        f"Saved ${savings:.6f} vs always-use-Opus baseline."
    )

    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Baseline Spend (all Opus)", f"${baseline_spend:.6f}")
    with col2:
        st.metric("Actual Spend", f"${total_spend:.6f}")
    with col3:
        st.metric("Money Saved", f"${savings:.6f}", delta=f"{savings_percent}% reduction")

    st.markdown("---")
    st.markdown("### ✂️ Token Optimization")

    col4, col5 = st.columns(2)
    with col4:
        st.metric(
            "Total Tokens Saved by Optimizer",
            f"{total_tokens_saved:,}",
            help="Tokens removed from prompts before sending to Claude"
        )
    with col5:
        avg_tokens_saved = (
            round(total_tokens_saved / total_requests, 1)
            if total_requests > 0 else 0
        )
        st.metric(
            "Avg Tokens Saved per Request",
            f"{avg_tokens_saved}"
        )

    st.markdown("---")
    st.markdown("### 📋 How This Works")
    st.markdown("""
    **Two cost reduction strategies combined:**

    **1. Prompt Optimizer**
    - Removes filler phrases ("Could you please", "I was wondering if")
    - Collapses extra whitespace
    - Removes repeated instructions
    - Result: fewer tokens sent → lower cost on every request

    **2. Complexity Analyzer**
    - Scores each prompt across task words, length, and risk signals
    - Simple tasks → Claude Haiku (187x cheaper than Opus per token)
    - Medium tasks → Claude Sonnet (balanced cost and quality)
    - High-risk or complex tasks → Claude Opus (best accuracy)
    - Result: right model for each job → no overpaying for simple work
    """)