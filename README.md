# LLM Cost Optimizer

> **Reduce your LLM API spend by up to 60% without changing your prompts or sacrificing quality.**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![Anthropic](https://img.shields.io/badge/Anthropic-Claude-orange.svg)](https://anthropic.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Executive Summary

LLM Cost Optimizer is an intelligent API gateway that sits between your application
and Anthropic's Claude models. It automatically routes each request to the most
cost-effective model capable of handling it, cleans prompts before sending to
reduce token usage, enforces team budget limits in real time, and provides a
live dashboard showing exactly where your LLM spend is going.

**Demonstrated results:** 60.8% cost reduction across 48 mixed requests,
saving $0.97 versus an always-use-best-model baseline — with zero change
to the quality of responses for appropriately routed tasks.

---

## The Business Problem

Most organisations using LLMs make one critical mistake: they send every
request to their most powerful — and most expensive — model by default.

This is the equivalent of hiring a senior consultant to answer a basic FAQ.
The answer is the same. The cost is not.

At scale, this default behaviour compounds rapidly:

| Scenario | Monthly Requests | Always Opus Cost | Optimized Cost | Monthly Saving |
|---|---|---|---|---|
| Small team (5 people) | 5,000 | ~$180 | ~$70 | ~$110 |
| Mid-size product (50 users) | 50,000 | ~$1,800 | ~$700 | ~$1,100 |
| Enterprise (500 users) | 500,000 | ~$18,000 | ~$7,000 | ~$11,000 |

*Estimates based on simulation results. Actual savings vary by prompt mix.*

Beyond raw cost, teams also lack visibility. Without knowing which team
is spending what, on which feature, using which model, cost management
is impossible. Budget overruns go unnoticed until the invoice arrives.

**LLM Cost Optimizer solves both problems simultaneously.**

---

## Solution Overview

The optimizer intercepts every LLM request before it reaches Claude
and applies four layers of cost control in sequence:

```
┌─────────────────────────────────────────────────────────────┐
│                    INCOMING REQUEST                         │
│         (prompt + team_id + feature_name + priority)        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 LAYER 1: BUDGET CHECK                       │
│                                                             │
│  Check if the requesting team is within their daily and    │
│  monthly budget limits before touching the LLM at all.     │
│                                                             │
│  Under 80%  → proceed normally                             │
│  80% - 100% → proceed with warning attached to response    │
│  Over 100%  → block low/medium priority requests           │
│               allow high priority through with warning     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               LAYER 2: PROMPT OPTIMIZER                     │
│                                                             │
│  Clean the prompt BEFORE choosing a model.                  │
│  Fewer tokens = lower cost regardless of model chosen.      │
│                                                             │
│  Removes: filler phrases ("could you please", "I was       │
│           wondering if you could", "kindly", etc.)         │
│  Fixes:   extra whitespace, duplicate sentences            │
│  Reports: tokens saved and percentage reduction            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│             LAYER 3: COMPLEXITY ANALYZER                    │
│                                                             │
│  Score the cleaned prompt and route to the cheapest        │
│  model that can genuinely handle the task.                 │
│                                                             │
│  Simple tasks   → claude-haiku   (187x cheaper than Opus)  │
│  Medium tasks   → claude-sonnet  (balanced cost/quality)   │
│  Complex tasks  → claude-opus    (best accuracy)           │
│                                                             │
│  Risk override: legal, medical, financial, compliance       │
│  keywords always force claude-opus regardless of score.    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   CLAUDE API CALL                           │
│                                                             │
│  Optimized prompt sent to the selected model.              │
│  Real token counts and cost returned in the response.      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                LAYER 4: COST LOGGER                         │
│                                                             │
│  Every request logged to SQLite with full audit trail:     │
│  timestamp, team, feature, model, tokens, cost,            │
│  latency, routing reason, and tokens saved.                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               RESPONSE RETURNED TO CALLER                   │
│   Includes: answer + model used + cost + routing reason    │
└─────────────────────────────────────────────────────────────┘
```

---

## How This Benefits Enterprises and Teams

### 1. Finance and Procurement

**Problem:** LLM costs appear as a single line item on a cloud bill.
There is no visibility into which team, product, or feature drove the spend.

**What LLM Cost Optimizer provides:**
- Per-team daily and monthly budget limits enforced automatically
- Real-time spend tracking by team and by feature name
- Automatic blocking when budgets are exhausted
- Full audit trail queryable by date, team, model, or cost
- Live dashboard with spend trends exportable for finance reporting

**Business outcome:** Finance teams can set budgets, track actuals,
and hold product teams accountable for LLM spend — the same way
they manage cloud infrastructure costs today.

---

### 2. Engineering and Platform Teams

**Problem:** Every developer makes their own decision about which model
to use. Some always pick the best model out of habit. Others forget to
update when a cheaper option becomes available. There is no consistent policy.

**What LLM Cost Optimizer provides:**
- Centralised routing policy owned and maintained by the platform team
- Model selection removed from individual developer decisions entirely
- New models added to the registry in one file — all services benefit immediately
- High-risk domain detection prevents cheap models being used where accuracy matters
- Error handling and fallback logic built into the gateway once, not duplicated everywhere

**Business outcome:** Platform teams own one integration point.
Product teams call one endpoint. Model selection, cost tracking,
and budget enforcement are handled transparently in the background.

---

### 3. Product and Growth Teams

**Problem:** Features using LLMs have unpredictable costs. A spike in
usage can exhaust the monthly budget before the team is aware.
There is no early warning system.

**What LLM Cost Optimizer provides:**
- Per-feature cost tracking via the `feature_name` field on every request
- Budget warnings at 80% utilisation — before limits are hit
- Priority field allows critical features to punch through budget limits
- Routing reason in every response explains which model was used and why
- Dashboard showing the most expensive features ranked by total spend

**Business outcome:** Product managers can see exactly which feature
is the most expensive, set appropriate budgets per feature, and make
data-driven decisions about where to invest in optimisation.

---

### 4. Data and Analytics Teams

**Problem:** There is no historical record of LLM usage at the request level.
It is impossible to answer: "How much did we spend on the recommendation
feature last month?" or "Which model gives the best latency for our use case?"

**What LLM Cost Optimizer provides:**
- Every request stored in SQLite with full metadata
- Queryable by team, feature, model, date range, or cost
- Latency tracking per model for performance benchmarking
- Token savings tracked over time to measure prompt engineering ROI
- Dashboard with spend trends, model breakdown, and savings vs baseline report

**Business outcome:** Data teams have a structured, queryable dataset
of every LLM interaction in the organisation. This enables cost forecasting,
usage anomaly detection, and evidence-based model selection decisions.

---

### 5. Legal, Compliance, and Risk Teams

**Problem:** Cheap models are sometimes used for high-stakes tasks
where accuracy is non-negotiable — legal review, medical summarisation,
financial analysis. This introduces unacceptable quality risk that is
invisible to the teams responsible for it.

**What LLM Cost Optimizer provides:**
- Automatic detection of high-risk keywords in every prompt
- Hard override to Claude Opus for any legal, medical, financial,
  compliance, or security-related request — regardless of caller priority
- Routing reason logged on every single request as auditable evidence
  of which model handled which task and why

**Business outcome:** Risk and compliance teams have a documented,
infrastructure-enforced policy guaranteeing high-stakes tasks always
use the highest quality model. This cannot be bypassed by developer
error or forgotten configuration.

---

## Demonstrated Results

Real simulation across 48 mixed requests spanning five teams and ten feature types:

| Metric | Value |
|---|---|
| Total requests processed | 48 |
| Baseline cost (all Claude Opus) | $1.602480 |
| Actual cost (smart routing) | $0.628808 |
| Total saved | $0.973672 |
| **Cost reduction** | **60.8%** |
| Tokens saved by prompt optimizer | 31 |

**Portfolio headline:**

> "Reduced LLM spend by 60.8% across 48 requests by implementing
> complexity-based model routing and prompt optimization, saving
> $0.97 versus an always-use-best-model baseline."

---

## Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| API Gateway | FastAPI (Python) | Receives all requests, orchestrates all layers |
| LLM Provider | Anthropic Claude | Haiku, Sonnet, and Opus model tiers |
| Routing Engine | Custom Python | Complexity scoring and model tier selection |
| Prompt Optimizer | Python + regex | Token reduction before model selection |
| Database | SQLite | Request logs, budget tables, audit trail |
| Dashboard | Streamlit | Real-time cost visibility and savings reporting |
| Config Management | python-dotenv | API key and environment variable management |

---

## Project Structure

```
LLM-Cost-Optimizer/
│
├── main.py                      # FastAPI app entry point and request orchestration
├── simulate.py                  # Workload simulation and cost savings report
├── requirements.txt             # All Python dependencies
├── .env.example                 # Environment variable template (no secrets)
│
├── schemas/
│   └── request.py               # LLMRequest and LLMResponse data models
│
├── models/
│   └── registry.py              # Model catalogue: names, tiers, and pricing
│
├── router/
│   ├── complexity_analyzer.py   # Prompt scoring and model tier selection
│   └── prompt_optimizer.py      # Filler removal and token count reduction
│
├── providers/
│   ├── base.py                  # Abstract provider contract (extensible)
│   └── anthropic_adapter.py     # Anthropic API integration and cost calculation
│
├── tracker/
│   ├── database.py              # SQLite initialisation, tables, and connection
│   ├── logger.py                # Request logging and spend aggregation queries
│   └── budget.py                # Budget limit enforcement and status checking
│
└── dashboard/
    └── app.py                   # Streamlit dashboard: spend, models, savings
```

---

## API Reference

### POST `/llm/request`

Submit a prompt for optimized routing and processing.

**Request body:**
```json
{
  "prompt": "Analyze the competitive risks of entering the European EV market.",
  "team_id": "strategy",
  "feature_name": "market_analysis",
  "priority": "low"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `prompt` | string | Yes | The instruction or question for Claude |
| `team_id` | string | Yes | Team identifier for budget tracking |
| `feature_name` | string | Yes | Feature name for cost breakdown |
| `priority` | string | No | `"low"`, `"medium"`, or `"high"`. Default: `"medium"` |
| `preferred_model` | string | No | Bypass routing and use this model directly |

**Response:**
```json
{
  "text": "The European EV market presents several competitive risks...",
  "model_used": "claude-opus-4-6",
  "tokens_input": 18,
  "tokens_output": 312,
  "cost": 0.00023670,
  "latency_ms": 1842.5,
  "routing_reason": "High-risk domain detected (financial). Forced to Tier 3.",
  "tokens_saved": 0,
  "percent_saved": 0.0
}
```

---

### GET `/models`

Returns the full model registry with pricing and tier information.

### GET `/spend/{team_id}`

Returns daily and monthly spend for a specific team with budget utilisation.

### GET `/spend`

Returns spend breakdown by team and by model across all time.

### GET `/health`

Health check. Returns service status and version.

---

## Routing Decision Logic

```
Is preferred_model set?
  YES → use that model directly. Still optimize the prompt first.

Is priority "high"?
  YES → Claude Opus. No analysis needed. Skip to API call.

Otherwise:
  Step 1 — Optimize the prompt
    Remove filler phrases ("could you please", "I was wondering if", etc.)
    Collapse extra whitespace and blank lines
    Remove duplicate sentences

  Step 2 — Analyze complexity
    Check for risk keywords:
      legal, law, contract, compliance, medical, diagnosis,
      financial, investment, tax, audit, security, vulnerability
      → If any found: force Tier 3. Stop scoring.

    Score task words in the prompt:
      Simple  (list, what, define, translate, find) → +1 each
      Medium  (summarize, write, explain, draft)    → +2 each
      Complex (analyze, evaluate, compare, design)  → +3 each

    Score prompt length:
      Under 20 words → +0
      20 to 80 words → +2
      Over 80 words  → +5

    Structured output requested (JSON, table, CSV, schema)?
      → +3

  Step 3 — Convert score to model tier
    Score 0 to 3  → Tier 1 → Claude Haiku   (cheapest, fastest)
    Score 4 to 8  → Tier 2 → Claude Sonnet  (balanced)
    Score 9+      → Tier 3 → Claude Opus    (best quality)

  Step 4 — Apply priority floor
    Priority "medium" = minimum Tier 2, even if score says Tier 1
    Never route below what the caller's priority implies
```

---

## Setup and Installation

### Prerequisites

- Python 3.11 or higher
- An Anthropic API key from [console.anthropic.com](https://console.anthropic.com)
- Git Bash or any terminal

### Installation

```bash
# Clone the repository
git clone https://github.com/beawesome8/LLM-Cost-Optimizer.git
cd LLM-Cost-Optimizer

# Create and activate virtual environment
python -m venv venv
source venv/Scripts/activate      # Windows Git Bash
# source venv/bin/activate        # Mac or Linux

# Install all dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Open .env and add: ANTHROPIC_API_KEY=your_key_here
```

### Run the API Server

```bash
python main.py
```

- Server: `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`

### Run the Dashboard

```bash
streamlit run dashboard/app.py
```

- Dashboard: `http://localhost:8501`

### Run the Cost Simulation

```bash
python simulate.py
```

Sends 50 mixed prompts and prints a full savings report.

---

## Build History

Built and delivered in five tracked phases with a tagged GitHub release at each milestone:

| Tag | Phase | Delivered |
|---|---|---|
| `v1.0-foundation` | Project Foundation | FastAPI gateway, model registry, Anthropic provider |
| `v2.0-smart-routing` | Smart Routing | Complexity analyzer, prompt optimizer, automatic model selection |
| `v3.0-cost-tracking` | Cost Tracking | SQLite logging, spend queries, budget enforcement |
| `v4.0-dashboard` | Dashboard | Streamlit UI with team spend, model usage, savings report |
| `v5.0-portfolio-ready` | Portfolio Polish | Simulation, real savings numbers, enterprise documentation |

---

## Model Pricing Reference

| Model | Tier | Input / 1K tokens | Output / 1K tokens | Best For |
|---|---|---|---|---|
| claude-haiku-4-5 | 1 (Cheapest) | $0.00008 | $0.00025 | Q&A, extraction, translation, formatting |
| claude-sonnet-4-6 | 2 (Balanced) | $0.003 | $0.015 | Summarisation, drafting, classification |
| claude-opus-4-6 | 3 (Best) | $0.015 | $0.075 | Complex reasoning, legal, financial, medical |

*Claude Opus costs 187x more per input token than Claude Haiku.
Smart routing ensures Opus is only used when the task genuinely requires it.*

---

## Extending the System

The architecture is designed to be extended without breaking existing behaviour:

**Add a new model:** Add one entry to `models/registry.py`. No other file changes needed.

**Add a new provider:** Create a new class in `providers/` that inherits from `BaseProvider`
and implements the `call()` method. Register it in `main.py`.

**Add a new budget rule:** Extend `tracker/budget.py` with new logic.
The rest of the system is unaffected.

**Add a new routing signal:** Add scoring logic to `router/complexity_analyzer.py`.

---

## Author

**Aman Benjamin Emmanuel**
AI Engineer | Munich, Germany

- GitHub: [beawesome8](https://github.com/beawesome8)
- LinkedIn: [linkedin.com/in/beawesome8](https://linkedin.com/in/beawesome8)
- Email: benemmanuel80@gmail.com

---

*For full implementation details, architecture decisions, and step-by-step
build notes, see [project_implementation.md](project_implementation.md).*