# LLM Cost Optimizer

A production-grade API gateway that sits between your application and Anthropic's Claude models.
It automatically analyzes prompt complexity, optimizes tokens before sending, routes each request
to the most cost-effective model, tracks spending by team and feature, and exposes a real-time
cost dashboard.

**Built with:** Python, FastAPI, SQLite, Streamlit, Anthropic API

**Author:** Aman Benjamin Emmanuel
**GitHub:** [beawesome8](https://github.com/beawesome8)

---

## The Problem This Solves

Most teams using LLMs send every request to their most powerful (and most expensive) model by default.
This is like hiring a senior surgeon to put on a bandage. A simple question like "What is the capital
of France?" does not need Claude Opus. It needs Claude Haiku, which costs 187x less per token.

At scale, this default behavior wastes thousands of dollars per month.

**LLM Cost Optimizer fixes this automatically.**

---

## How It Works

Every request passes through three layers before reaching Claude:

```
Incoming Request
      │
      ▼
┌─────────────────────┐
│  Prompt Optimizer   │  Strips filler, collapses whitespace,
│                     │  removes repeated instructions.
│  Fewer tokens sent  │  Saves cost before the model is even chosen.
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Complexity Analyzer │  Reads the prompt and scores it.
│                     │  Simple task → Tier 1 (Haiku, cheapest).
│  Right model chosen │  Medium task → Tier 2 (Sonnet, balanced).
│                     │  Complex/risky → Tier 3 (Opus, best).
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   Cost Tracker      │  Logs every request to SQLite.
│                     │  Tracks tokens, cost, model, team, feature.
│  Full audit trail   │  Enforces daily and monthly budget limits.
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   Claude (API)      │  Only now does the request reach Claude.
│                     │  With a cleaner prompt and the right model.
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Dashboard          │  Streamlit UI showing spend by team,
│                     │  savings vs baseline, model usage breakdown.
└─────────────────────┘
```

---

## Project Structure

```
LLM-Cost-Optimizer/
│
├── main.py                     # FastAPI app entry point
├── requirements.txt            # All Python dependencies
├── .env.example                # Template for environment variables
├── .gitignore                  # Files Git should ignore
├── README.md                   # This file
│
├── schemas/                    # Data shapes and validation
│   ├── __init__.py
│   └── request.py              # LLMRequest and LLMResponse models
│
├── models/                     # Model registry (menu of available models)
│   ├── __init__.py
│   └── registry.py             # Model names, tiers, and pricing
│
├── router/                     # Routing and optimization logic
│   ├── __init__.py
│   ├── complexity_analyzer.py  # Scores prompt complexity → picks tier
│   └── prompt_optimizer.py     # Cleans prompt → reduces tokens
│
├── providers/                  # LLM provider adapters
│   ├── __init__.py
│   ├── base.py                 # Abstract base class (the contract)
│   └── anthropic_adapter.py    # Calls Anthropic API, returns standard response
│
├── tracker/                    # Cost tracking and budget enforcement
│   ├── __init__.py
│   ├── database.py             # SQLite setup and connection
│   ├── logger.py               # Logs every request to the database
│   └── budget.py               # Budget policies and enforcement
│
└── dashboard/                  # Streamlit cost visibility UI
    ├── __init__.py
    └── app.py                  # Dashboard: spend by team, savings, model usage
```

---

## Build Phases

This project is built in 5 phases. Each phase produces working, testable code.

---

### Phase 1 — Project Foundation (Day 1)

**Goal:** Set up the project skeleton. Every folder, file, and dependency in place.
By the end of this phase you can run the server and hit a health check endpoint.

**What you build:**
- Folder structure
- Virtual environment
- requirements.txt
- .env and .gitignore
- schemas/request.py (LLMRequest and LLMResponse shapes)
- models/registry.py (model menu with tiers and pricing)
- providers/base.py (abstract contract for all providers)
- providers/anthropic_adapter.py (actual Anthropic API call)
- main.py (FastAPI app, health endpoint, models endpoint)

**Test:** Server starts. `/health` returns OK. `/models` lists all Claude models.

---

### Phase 2 — Smart Routing (Day 2)

**Goal:** Make the system automatically choose the right model instead of always using the most expensive one.

**What you build:**
- router/prompt_optimizer.py
  - Remove filler phrases ("could you please", "I was wondering")
  - Collapse whitespace
  - Remove duplicate sentences
  - Estimate and report token savings
- router/complexity_analyzer.py
  - Score the prompt using task words, length, risk keywords
  - Output a tier: 1 (cheap), 2 (balanced), 3 (best)
  - Force Tier 3 for legal, medical, financial, compliance prompts
- Wire both into main.py
  - Optimize FIRST, then analyze, then route

**Test:** Send a simple prompt and a complex prompt both with priority "low".
The simple one routes to Haiku. The complex one auto-escalates to Opus.

---

### Phase 3 — Cost Tracking (Day 3)

**Goal:** Log every request to a database so you can see exactly where money is going.

**What you build:**
- tracker/database.py
  - SQLite database setup
  - requests table: timestamp, team_id, feature_name, model_used,
    tokens_input, tokens_output, cost, latency_ms, routing_reason
  - budgets table: team_id, daily_limit, monthly_limit
- tracker/logger.py
  - log_request(): writes one row per request
  - get_team_spend(): returns total spend for a team today and this month
- tracker/budget.py
  - check_budget(): returns OK, WARNING (80%), or BLOCKED (100%)
  - Block low-priority requests when budget is at 100%
  - Return a clear error instead of silently failing
- Wire into main.py
  - Check budget BEFORE calling Claude
  - Log result AFTER Claude responds

**Test:** Send 10 requests. Query the database. See cost breakdown by team.
Simulate a budget breach and confirm the block behavior.

---

### Phase 4 — Cost Dashboard (Day 4)

**Goal:** Make cost data visible to humans through a real UI.

**What you build:**
- dashboard/app.py (Streamlit)
  - Total spend today and this month
  - Spend by team (bar chart)
  - Spend by model (pie chart)
  - Savings estimate: actual cost vs "everything sent to Opus" baseline
  - Most expensive prompts table
  - Routing breakdown: how many requests went to each tier

**Test:** Run the dashboard. See all charts populated from the SQLite database.
The savings number is the headline metric for your portfolio case study.

---

### Phase 5 — Portfolio Polish (Day 5)

**Goal:** Make the project presentable on GitHub and in interviews.

**What you build:**
- Simulated workload script: send 50 mixed prompts through the gateway
  and generate a cost savings report
- Final README with architecture diagram, setup instructions,
  example requests, and the case study headline metric
- GitHub push with clean commit history

**Result:** A project you can demo live in any interview and explain end to end.

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/beawesome8/LLM-Cost-Optimizer.git
cd LLM-Cost-Optimizer
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Add Your API Key

```bash
cp .env.example .env
# Open .env and add your Anthropic API key
```

### 5. Run the Server

```bash
python main.py
```

Server runs at: `http://localhost:8000`
API docs at: `http://localhost:8000/docs`

### 6. Run the Dashboard (Phase 4+)

```bash
streamlit run dashboard/app.py
```

Dashboard runs at: `http://localhost:8501`

---

## Example Request

```bash
curl -X POST http://localhost:8000/llm/request \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is the capital of France?",
    "team_id": "marketing",
    "feature_name": "qa_bot",
    "priority": "low"
  }'
```

Example response:

```json
{
  "text": "Paris.",
  "model_used": "claude-haiku-4-5",
  "tokens_input": 8,
  "tokens_output": 2,
  "cost": 0.00000064,
  "latency_ms": 312.5
}
```

The same request sent to Claude Opus would cost 187x more. The optimizer chose Haiku automatically.

---

## Model Tiers and Pricing

| Tier | Model | Input per 1K tokens | Output per 1K tokens | Best For |
|------|-------|--------------------|--------------------|----------|
| 1 | claude-haiku-4-5 | $0.00008 | $0.00025 | Simple Q&A, extraction, formatting |
| 2 | claude-sonnet-4-6 | $0.003 | $0.015 | Summarization, drafting, classification |
| 3 | claude-opus-4-6 | $0.015 | $0.075 | Reasoning, analysis, high-stakes tasks |

---

## Routing Logic

```
Is preferred_model set?
  YES → use it directly

Is priority "high"?
  YES → use Tier 3 (Opus)

Otherwise:
  1. Optimize the prompt (remove filler, collapse whitespace)
  2. Analyze prompt complexity:
     - Contains risk keywords (legal, medical, financial)? → Tier 3
     - Complex task words (analyze, evaluate, compare)? → score +3 each
     - Medium task words (summarize, explain, write)? → score +2 each
     - Simple task words (list, what, when, define)? → score +1 each
     - Long prompt (150+ words)? → score +5
     - Structured output required (JSON, table)? → score +3
  3. Score → Tier:
     - Score 0-3   → Tier 1 (Haiku)
     - Score 4-8   → Tier 2 (Sonnet)
     - Score 9+    → Tier 3 (Opus)
  4. Never route BELOW the user's stated priority tier
```

---

## Portfolio Case Study Headline

> "Reduced simulated LLM spend by 73% across 50 mixed prompts by implementing
> complexity-based model routing and prompt optimization, while maintaining
> response quality through automatic tier escalation for high-risk domains."

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| API Gateway | FastAPI | Receives and routes all LLM requests |
| LLM Provider | Anthropic Claude | Haiku, Sonnet, and Opus models |
| Routing | Custom Python | Complexity scoring and tier selection |
| Optimization | Custom Python + regex | Token reduction before sending |
| Storage | SQLite | Request logs and budget tracking |
| Dashboard | Streamlit | Cost visibility and savings reporting |
| Environment | python-dotenv | API key and config management |

---

## What This Project Demonstrates

- **LLMOps thinking:** Cost is a first-class concern, not an afterthought
- **Systems design:** A layered architecture where each component has one job
- **Production habits:** Audit logging, budget enforcement, error handling
- **Business awareness:** Savings are measured and reported, not assumed

---

*Built as a portfolio project demonstrating applied AI engineering skills.*
*Part of an active job search targeting AI Engineer and ML Engineer roles in Germany.*