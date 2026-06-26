import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from schemas.request import LLMRequest, LLMResponse
from providers.anthropic_adapter import AnthropicProvider
from models.registry import registry
from router.prompt_optimizer import optimize_prompt
from router.complexity_analyzer import analyze_complexity
from tracker.database import initialize_database
from tracker.logger import log_request
from tracker.budget import check_budget

load_dotenv()

app = FastAPI(
    title="LLM Cost Optimizer",
    description=(
        "Routes LLM requests to the cheapest capable Claude model. "
        "Tracks cost per team and enforces budget limits."
    ),
    version="3.0.0"
)

# -----------------------------------------------------------------------
# Initialize the database when the server starts.
# Creates tables if they don't exist. Safe to run every time.
# -----------------------------------------------------------------------
initialize_database()

anthropic_provider = AnthropicProvider()


def _route_request(
    prompt: str,
    priority: str,
    preferred_model: str | None
) -> dict:
    """
    Optimize the prompt and route to the right model tier.

    Step 1: Optimize prompt (remove filler, normalize whitespace)
    Step 2: Analyze complexity (score prompt → pick tier)
    Step 3: Return model name + cleaned prompt + routing info

    Args:
        prompt         : Raw prompt from the user.
        priority       : "low", "medium", or "high".
        preferred_model: Optional direct model override.

    Returns:
        dict with model_name, optimized_prompt, routing_reason,
        tokens_saved, percent_saved.
    """
    # Step 1: Always optimize first
    optimization = optimize_prompt(prompt)
    optimized_prompt = optimization["optimized_prompt"]
    tokens_saved = optimization["tokens_saved"]
    percent_saved = optimization["percent_saved"]

    # User override — skip routing logic
    if preferred_model:
        return {
            "model_name": preferred_model,
            "optimized_prompt": optimized_prompt,
            "routing_reason": (
                f"User-specified model: {preferred_model}. "
                f"Prompt optimized: {tokens_saved} tokens saved ({percent_saved}%)."
            ),
            "tokens_saved": tokens_saved,
            "percent_saved": percent_saved,
            "original_prompt": prompt
        }

    # High priority → always best model
    if priority == "high":
        tier_models = registry.get_by_tier(3)
        return {
            "model_name": tier_models[0].name,
            "optimized_prompt": optimized_prompt,
            "routing_reason": (
                f"Priority 'high' → Tier 3 (best model). "
                f"Prompt optimized: {tokens_saved} tokens saved ({percent_saved}%)."
            ),
            "tokens_saved": tokens_saved,
            "percent_saved": percent_saved,
            "original_prompt": prompt
        }

    # Step 2: Analyze complexity of the cleaned prompt
    analysis = analyze_complexity(optimized_prompt)
    analyzed_tier = analysis["tier"]

    # Never route below the user's stated priority floor
    priority_floor = {"low": 1, "medium": 2}
    min_tier = priority_floor.get(priority, 1)
    final_tier = max(analyzed_tier, min_tier)

    tier_models = registry.get_by_tier(final_tier)
    if not tier_models:
        raise ValueError(f"No models found for tier {final_tier}")

    return {
        "model_name": tier_models[0].name,
        "optimized_prompt": optimized_prompt,
        "routing_reason": (
            analysis["reason"] +
            f" Prompt optimized: {tokens_saved} tokens saved ({percent_saved}%)."
        ),
        "tokens_saved": tokens_saved,
        "percent_saved": percent_saved,
        "original_prompt": prompt
    }


@app.post("/llm/request", response_model=LLMResponse)
async def process_request(req: LLMRequest) -> LLMResponse:
    """
    Main endpoint. Full flow:
        1. Check team budget → block if over limit
        2. Optimize prompt → fewer tokens = lower cost
        3. Analyze complexity → pick right model
        4. Call Claude
        5. Log everything to database
        6. Return response
    """
    try:
        # -----------------------------------------------------------
        # STEP 1: Budget check BEFORE calling Claude
        # If blocked, we return an error immediately.
        # Claude is never called. No cost is incurred.
        # -----------------------------------------------------------
        budget_status = check_budget(req.team_id, req.priority)

        if budget_status["status"] == "blocked":
            raise HTTPException(
                status_code=429,
                detail=budget_status["message"]
            )

        # -----------------------------------------------------------
        # STEP 2 + 3: Route the request (optimize + analyze)
        # -----------------------------------------------------------
        routing = _route_request(
            prompt=req.prompt,
            priority=req.priority,
            preferred_model=req.preferred_model
        )

        # -----------------------------------------------------------
        # STEP 4: Call Claude with the optimized prompt
        # -----------------------------------------------------------
        response = anthropic_provider.call(
            model_name=routing["model_name"],
            prompt=routing["optimized_prompt"],
            routing_info={
                "routing_reason": routing["routing_reason"],
                "tokens_saved": routing["tokens_saved"],
                "percent_saved": routing["percent_saved"]
            }
        )

        # -----------------------------------------------------------
        # STEP 5: Log the request to the database
        # We do this AFTER getting the response so we have real
        # token counts and cost from Anthropic (not estimates).
        # If logging fails, we still return the response — the user
        # already got their answer.
        # -----------------------------------------------------------
        log_request(
            team_id=req.team_id,
            feature_name=req.feature_name,
            model_used=response.model_used,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            cost=response.cost,
            latency_ms=response.latency_ms,
            routing_reason=response.routing_reason,
            tokens_saved=response.tokens_saved,
            percent_saved=response.percent_saved,
            original_prompt=routing.get("original_prompt", ""),
            optimized_prompt=routing["optimized_prompt"]
        )

        # -----------------------------------------------------------
        # STEP 6: Add budget warning to response if applicable
        # The response still goes through — just with a note attached
        # -----------------------------------------------------------
        if budget_status["status"] == "warning":
            response.routing_reason = (
                response.routing_reason +
                f" | {budget_status['message']}"
            )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions (budget blocked, etc.)
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/spend/{team_id}")
def get_team_spend_endpoint(team_id: str):
    """
    Returns how much a team has spent today and this month.

    Visit http://localhost:8000/spend/marketing to check marketing's spend.

    Args:
        team_id: The team name in the URL path.
    """
    from tracker.logger import get_team_spend
    from tracker.budget import get_team_budget

    spend = get_team_spend(team_id)
    budget = get_team_budget(team_id)

    return {
        "team_id": team_id,
        "daily_spend": spend["daily_spend"],
        "daily_limit": budget["daily_limit"],
        "daily_percent_used": round(
            spend["daily_spend"] / budget["daily_limit"] * 100, 1
        ),
        "monthly_spend": spend["monthly_spend"],
        "monthly_limit": budget["monthly_limit"],
        "monthly_percent_used": round(
            spend["monthly_spend"] / budget["monthly_limit"] * 100, 1
        )
    }


@app.get("/spend")
def get_all_spend():
    """
    Returns spend breakdown by team and by model.
    Used by the dashboard in Phase 4.
    """
    from tracker.logger import get_spend_by_team, get_spend_by_model

    return {
        "by_team": get_spend_by_team(),
        "by_model": get_spend_by_model()
    }


@app.get("/models")
def list_models():
    """Returns all available models with pricing and tier info."""
    return {
        name: {
            "provider": model.provider,
            "quality_tier": model.quality_tier,
            "input_cost_per_1k_tokens": model.input_cost_per_1k_tokens,
            "output_cost_per_1k_tokens": model.output_cost_per_1k_tokens,
            "description": model.description
        }
        for name, model in registry.list_all().items()
    }


@app.get("/health")
def health_check():
    """Confirms the server is running."""
    return {
        "status": "ok",
        "service": "LLM Cost Optimizer",
        "version": "3.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)