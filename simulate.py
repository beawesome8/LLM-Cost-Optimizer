"""
simulate.py

Sends 50 mixed prompts through the LLM Cost Optimizer gateway
and prints a cost savings report at the end.

Run this AFTER starting the server with: python main.py

Then in a second terminal:
    python simulate.py

What this does:
    - Sends 50 prompts across different teams, features, and priorities
    - Prompts are intentionally mixed: simple, medium, and complex
    - Records actual cost from each response
    - Calculates what it would have cost to send everything to Opus
    - Prints a final savings report
"""

import requests
import json
import time
from typing import Optional


# -----------------------------------------------------------------------
# SERVER URL
# Make sure python main.py is running before you run this script.
# -----------------------------------------------------------------------
BASE_URL = "http://localhost:8000"


# -----------------------------------------------------------------------
# 50 MIXED PROMPTS
#
# Intentionally varied:
#   - Simple questions   → should route to Haiku   (cheapest)
#   - Medium tasks       → should route to Sonnet  (balanced)
#   - Complex analysis   → should route to Opus    (best)
#   - Some have filler   → optimizer should clean them
#   - Some have "financial/legal" → risk override to Opus
#
# This variety is what makes the savings story compelling.
# -----------------------------------------------------------------------
PROMPTS = [
    # ---- SIMPLE (expect Haiku) ----
    {
        "prompt": "What is the capital of Germany?",
        "team_id": "sales",
        "feature_name": "qa_bot",
        "priority": "low"
    },
    {
        "prompt": "What does API stand for?",
        "team_id": "engineering",
        "feature_name": "docs",
        "priority": "low"
    },
    {
        "prompt": "List the days of the week.",
        "team_id": "content",
        "feature_name": "formatter",
        "priority": "low"
    },
    {
        "prompt": "What is the currency of Japan?",
        "team_id": "sales",
        "feature_name": "qa_bot",
        "priority": "low"
    },
    {
        "prompt": "How many months are in a year?",
        "team_id": "marketing",
        "feature_name": "qa_bot",
        "priority": "low"
    },
    {
        "prompt": "What is the speed of light?",
        "team_id": "engineering",
        "feature_name": "qa_bot",
        "priority": "low"
    },
    {
        "prompt": "Translate 'Hello' to French.",
        "team_id": "content",
        "feature_name": "translator",
        "priority": "low"
    },
    {
        "prompt": "What is Python used for?",
        "team_id": "engineering",
        "feature_name": "qa_bot",
        "priority": "low"
    },
    {
        "prompt": "Name three types of machine learning.",
        "team_id": "engineering",
        "feature_name": "docs",
        "priority": "low"
    },
    {
        "prompt": "What does SQL stand for?",
        "team_id": "sales",
        "feature_name": "qa_bot",
        "priority": "low"
    },

    # ---- SIMPLE WITH FILLER (optimizer should strip these) ----
    {
        "prompt": "Could you please tell me what the capital of France is?",
        "team_id": "marketing",
        "feature_name": "qa_bot",
        "priority": "low"
    },
    {
        "prompt": "I was wondering if you could list the planets in our solar system.",
        "team_id": "content",
        "feature_name": "qa_bot",
        "priority": "low"
    },
    {
        "prompt": "Can you please define the word 'algorithm'?",
        "team_id": "engineering",
        "feature_name": "docs",
        "priority": "low"
    },
    {
        "prompt": "Would you be able to tell me what HTTP stands for?",
        "team_id": "sales",
        "feature_name": "qa_bot",
        "priority": "low"
    },
    {
        "prompt": "Could you kindly tell me what the largest country by area is?",
        "team_id": "strategy",
        "feature_name": "qa_bot",
        "priority": "low"
    },

    # ---- MEDIUM (expect Sonnet) ----
    {
        "prompt": "Summarize the key differences between supervised and unsupervised learning.",
        "team_id": "engineering",
        "feature_name": "docs",
        "priority": "low"
    },
    {
        "prompt": "Explain how a REST API works in simple terms.",
        "team_id": "engineering",
        "feature_name": "docs",
        "priority": "low"
    },
    {
        "prompt": "Write a short product description for a noise-cancelling headphone.",
        "team_id": "marketing",
        "feature_name": "copywriter",
        "priority": "medium"
    },
    {
        "prompt": "Summarize the main advantages of cloud computing for small businesses.",
        "team_id": "sales",
        "feature_name": "pitch_helper",
        "priority": "low"
    },
    {
        "prompt": "Explain the difference between machine learning and deep learning.",
        "team_id": "content",
        "feature_name": "writer",
        "priority": "low"
    },
    {
        "prompt": "Draft a short follow-up email after a product demo.",
        "team_id": "sales",
        "feature_name": "email_writer",
        "priority": "medium"
    },
    {
        "prompt": "Describe the benefits of using Docker for software development.",
        "team_id": "engineering",
        "feature_name": "docs",
        "priority": "low"
    },
    {
        "prompt": "Summarize what an LLM is and how it works.",
        "team_id": "content",
        "feature_name": "writer",
        "priority": "low"
    },
    {
        "prompt": "Write a brief introduction paragraph about artificial intelligence for a blog post.",
        "team_id": "marketing",
        "feature_name": "copywriter",
        "priority": "medium"
    },
    {
        "prompt": "Explain the concept of prompt engineering in simple terms.",
        "team_id": "engineering",
        "feature_name": "docs",
        "priority": "low"
    },

    # ---- MEDIUM WITH FILLER ----
    {
        "prompt": "Could you please summarize the key benefits of agile project management?",
        "team_id": "strategy",
        "feature_name": "docs",
        "priority": "medium"
    },
    {
        "prompt": "I would like you to explain how neural networks learn from data.",
        "team_id": "engineering",
        "feature_name": "docs",
        "priority": "low"
    },
    {
        "prompt": "Can you please write a short paragraph describing the importance of data privacy?",
        "team_id": "content",
        "feature_name": "writer",
        "priority": "medium"
    },

    # ---- COMPLEX (expect Opus) ----
    {
        "prompt": "Analyze the competitive advantages and disadvantages of a startup entering the German electric vehicle market in 2026.",
        "team_id": "strategy",
        "feature_name": "market_analysis",
        "priority": "low"
    },
    {
        "prompt": "Compare and contrast microservices architecture versus monolithic architecture. Evaluate which is better for a fast-growing fintech startup.",
        "team_id": "engineering",
        "feature_name": "architecture_review",
        "priority": "low"
    },
    {
        "prompt": "Evaluate the strategic tradeoffs of expanding into three Asian markets simultaneously versus a staged rollout for a B2B SaaS company.",
        "team_id": "strategy",
        "feature_name": "strategy_analysis",
        "priority": "low"
    },
    {
        "prompt": "Analyze the long-term implications of large language models on the future of software engineering jobs. Consider automation risk, new roles, and skill requirements.",
        "team_id": "strategy",
        "feature_name": "research",
        "priority": "low"
    },
    {
        "prompt": "Design a data architecture for a real-time recommendation system that handles one million users. Consider latency, scalability, and cost tradeoffs.",
        "team_id": "engineering",
        "feature_name": "architecture_review",
        "priority": "low"
    },

    # ---- RISK OVERRIDE (financial/legal — expect Opus) ----
    {
        "prompt": "Summarize the key clauses I should review in a software licensing contract.",
        "team_id": "strategy",
        "feature_name": "legal_review",
        "priority": "low"
    },
    {
        "prompt": "What are the main financial risks of taking on venture capital funding for an early-stage startup?",
        "team_id": "strategy",
        "feature_name": "financial_planning",
        "priority": "low"
    },
    {
        "prompt": "Explain the key compliance requirements for storing user data under GDPR.",
        "team_id": "engineering",
        "feature_name": "compliance",
        "priority": "low"
    },
    {
        "prompt": "What are the main tax implications of operating a business across multiple EU countries?",
        "team_id": "strategy",
        "feature_name": "financial_planning",
        "priority": "low"
    },
    {
        "prompt": "Summarize the key legal considerations when hiring contractors versus full-time employees in Germany.",
        "team_id": "strategy",
        "feature_name": "legal_review",
        "priority": "low"
    },

    # ---- MORE MIXED ----
    {
        "prompt": "What are the top 3 benefits of using FastAPI over Flask?",
        "team_id": "engineering",
        "feature_name": "docs",
        "priority": "low"
    },
    {
        "prompt": "Write a compelling subject line for a cold outreach email to a CTO.",
        "team_id": "sales",
        "feature_name": "email_writer",
        "priority": "medium"
    },
    {
        "prompt": "Explain what a vector database is and when you would use one.",
        "team_id": "engineering",
        "feature_name": "docs",
        "priority": "low"
    },
    {
        "prompt": "Analyze the pros and cons of using LangChain versus building custom LLM pipelines from scratch.",
        "team_id": "engineering",
        "feature_name": "architecture_review",
        "priority": "low"
    },
    {
        "prompt": "Could you please write a short LinkedIn post announcing a new AI product launch?",
        "team_id": "marketing",
        "feature_name": "social_media",
        "priority": "medium"
    },
    {
        "prompt": "What is retrieval augmented generation and why does it matter?",
        "team_id": "engineering",
        "feature_name": "docs",
        "priority": "low"
    },
    {
        "prompt": "Summarize the key differences between PostgreSQL and MongoDB for an application that stores user profiles.",
        "team_id": "engineering",
        "feature_name": "docs",
        "priority": "low"
    },
    {
        "prompt": "Evaluate the financial viability of building an in-house LLM versus using API providers for a 50-person company.",
        "team_id": "strategy",
        "feature_name": "financial_planning",
        "priority": "low"
    },
    {
        "prompt": "Design a prompt engineering strategy for a customer support chatbot that handles billing disputes.",
        "team_id": "engineering",
        "feature_name": "architecture_review",
        "priority": "low"
    },
    {
        "prompt": "List the main Python libraries used in data science.",
        "team_id": "content",
        "feature_name": "qa_bot",
        "priority": "low"
    },
    {
        "prompt": "What is the difference between precision and recall in machine learning?",
        "team_id": "engineering",
        "feature_name": "docs",
        "priority": "low"
    },
]


def send_request(prompt_data: dict) -> Optional[dict]:
    """
    Send one request to the LLM Cost Optimizer gateway.

    Args:
        prompt_data: dict with prompt, team_id, feature_name, priority.

    Returns:
        dict: The response JSON, or None if the request failed.
    """
    try:
        response = requests.post(
            f"{BASE_URL}/llm/request",
            json=prompt_data,
            timeout=60
        )

        if response.status_code == 200:
            return response.json()
        else:
            print(f"   ⚠️  Request failed: {response.status_code} — {response.text[:80]}")
            return None

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def print_report(results: list) -> None:
    """
    Print a formatted cost savings report after the simulation.

    Args:
        results: List of response dicts from successful requests.
    """
    if not results:
        print("\n❌ No successful results to report.")
        return

    # ---------------------------------------------------------------
    # CALCULATE METRICS
    # ---------------------------------------------------------------
    total_requests = len(results)
    actual_cost = sum(r["cost"] for r in results)
    total_tokens_input = sum(r["tokens_input"] for r in results)
    total_tokens_output = sum(r["tokens_output"] for r in results)
    total_tokens_saved = sum(r["tokens_saved"] for r in results)

    # Baseline: what if everything went to Opus?
    # Opus pricing (must match registry.py)
    opus_input_price = 0.015
    opus_output_price = 0.075

    baseline_cost = sum(
        (r["tokens_input"] / 1000 * opus_input_price) +
        (r["tokens_output"] / 1000 * opus_output_price)
        for r in results
    )

    savings = baseline_cost - actual_cost
    savings_percent = (savings / baseline_cost * 100) if baseline_cost > 0 else 0

    # Model usage breakdown
    model_counts = {}
    model_costs = {}
    for r in results:
        model = r["model_used"]
        model_counts[model] = model_counts.get(model, 0) + 1
        model_costs[model] = model_costs.get(model, 0.0) + r["cost"]

    # ---------------------------------------------------------------
    # PRINT THE REPORT
    # ---------------------------------------------------------------
    print("\n")
    print("=" * 60)
    print("       LLM COST OPTIMIZER — SIMULATION REPORT")
    print("=" * 60)

    print(f"\n📊 SUMMARY")
    print(f"   Total requests sent   : {total_requests}")
    print(f"   Successful responses  : {total_requests}")
    print(f"   Total tokens (input)  : {total_tokens_input:,}")
    print(f"   Total tokens (output) : {total_tokens_output:,}")
    print(f"   Tokens saved by optimizer: {total_tokens_saved:,}")

    print(f"\n💰 COST COMPARISON")
    print(f"   Baseline cost (all Opus) : ${baseline_cost:.6f}")
    print(f"   Actual cost (optimized)  : ${actual_cost:.6f}")
    print(f"   Total saved              : ${savings:.6f}")
    print(f"   Savings percentage       : {savings_percent:.1f}%")

    print(f"\n🤖 MODEL USAGE BREAKDOWN")
    for model, count in sorted(model_counts.items()):
        cost = model_costs[model]
        pct = count / total_requests * 100
        print(f"   {model:<30} {count:>3} requests ({pct:.0f}%)  ${cost:.6f}")

    print(f"\n🏆 PORTFOLIO HEADLINE")
    print(f"   \"Reduced LLM spend by {savings_percent:.0f}% across {total_requests}")
    print(f"   requests using complexity-based routing and prompt")
    print(f"   optimization. Saved ${savings:.6f} vs always-use-Opus baseline.\"")

    print("\n" + "=" * 60)
    print("✅ Simulation complete. Check your dashboard at:")
    print("   http://localhost:8501")
    print("=" * 60 + "\n")


def main():
    """
    Run the full simulation.

    Sends all 50 prompts one by one, waits 0.5 seconds between
    each to avoid rate limiting, then prints the savings report.
    """
    print("\n🚀 LLM Cost Optimizer — Starting Simulation")
    print(f"   Sending {len(PROMPTS)} prompts through the gateway...")
    print(f"   Server: {BASE_URL}")
    print("   Make sure python main.py is running!\n")

    # Quick health check before starting
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        if health.status_code != 200:
            print("❌ Server is not responding. Run: python main.py")
            return
        print("✅ Server is healthy. Starting simulation...\n")
    except Exception:
        print("❌ Cannot reach server at localhost:8000.")
        print("   Make sure you ran: python main.py")
        return

    results = []

    for i, prompt_data in enumerate(PROMPTS, 1):
        # Show progress
        print(f"   [{i:02d}/{len(PROMPTS)}] Sending: \"{prompt_data['prompt'][:55]}...\"")

        response = send_request(prompt_data)

        if response:
            results.append(response)
            print(
                f"           ✅ {response['model_used']:<30} "
                f"${response['cost']:.8f}  "
                f"saved {response['tokens_saved']} tokens"
            )
        else:
            print(f"           ❌ Failed")

        # Small delay to avoid rate limiting
        # Anthropic has rate limits on how many requests per minute
        time.sleep(0.5)

    # Print final report
    print_report(results)


if __name__ == "__main__":
    main()