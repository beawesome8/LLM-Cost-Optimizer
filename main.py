import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from schemas.request import LLMRequest, LLMResponse
from providers.anthropic_adapter import AnthropicProvider
from models.registry import registry
from router.prompt_optimizer import optimize_prompt
from router.complexity_analyzer import analyze_complexity

load_dotenv()

app = FastAPI(
    title="LLM Cost Optimizer",
    description=(
        "Routes LLM requests to the cheapest capable Claude model. "
        "Optimizes prompts before sending to reduce token usage."
    ),
    version="2.0.0"
)

anthropic_provider = AnthropicProvider()


def _route_request(
    prompt: str,
    priority: str,
    preferred_model: str | None
) -> dict:
    """
    The smart routing function. Replaces the simple priority mapping.

    Two-step process:
        Step 1 — Prompt Optimization
            Clean the prompt before anything else.
            Fewer tokens = lower cost regardless of which model is chosen.

        Step 2 — Complexity Analysis
            Read the cleaned prompt and score its complexity.
            Use that score to pick the right model tier.

    Priority still matters:
        "high"   → always use Tier 3, skip analysis
        "medium" → analyze, but never go below Tier 2
        "low"    → analyze freely, use cheapest that fits

    preferred_model overrides everything.

    Args:
        prompt         : The raw prompt from the user.
        priority       : "low", "medium", or "high".
        preferred_model: Optional direct model override.

    Returns:
        dict: {
            "model_name"      : str,   the chosen model
            "optimized_prompt": str,   cleaned prompt to send
            "routing_reason"  : str,   why this model was chosen
            "tokens_saved"    : int,   tokens removed by optimizer
            "percent_saved"   : float  percentage saved
        }
    """

    # -------------------------------------------------------------------
    # STEP 1: Optimize the prompt
    # Always do this first, regardless of routing outcome.
    # Even if the user specifies a preferred model, we still clean
    # the prompt — because fewer tokens always means lower cost.
    # -------------------------------------------------------------------
    optimization = optimize_prompt(prompt)
    optimized_prompt = optimization["optimized_prompt"]
    tokens_saved = optimization["tokens_saved"]
    percent_saved = optimization["percent_saved"]

    # -------------------------------------------------------------------
    # OVERRIDE: User specified a model directly
    # Skip all routing logic. Use their choice. Still use clean prompt.
    # -------------------------------------------------------------------
    if preferred_model:
        return {
            "model_name": preferred_model,
            "optimized_prompt": optimized_prompt,
            "routing_reason": (
                f"User-specified model: {preferred_model}. "
                f"Prompt optimized: {tokens_saved} tokens saved "
                f"({percent_saved}%)."
            ),
            "tokens_saved": tokens_saved,
            "percent_saved": percent_saved
        }

    # -------------------------------------------------------------------
    # HIGH PRIORITY: Always use best model
    # No need to analyze — correctness matters most here.
    # -------------------------------------------------------------------
    if priority == "high":
        tier_models = registry.get_by_tier(3)
        return {
            "model_name": tier_models[0].name,
            "optimized_prompt": optimized_prompt,
            "routing_reason": (
                f"Priority 'high' → Tier 3 (best model). "
                f"Prompt optimized: {tokens_saved} tokens saved "
                f"({percent_saved}%)."
            ),
            "tokens_saved": tokens_saved,
            "percent_saved": percent_saved
        }

    # -------------------------------------------------------------------
    # STEP 2: Analyze complexity of the cleaned prompt
    # -------------------------------------------------------------------
    analysis = analyze_complexity(optimized_prompt)
    analyzed_tier = analysis["tier"]

    # -------------------------------------------------------------------
    # FLOOR RULE: Never route below what the user's priority implies
    #
    # Example: User says "medium" (implies at least Tier 2).
    # Analyzer says Tier 1. We use Tier 2 — never under-serve.
    #
    # But if analyzer says Tier 3 and user said "medium",
    # we use Tier 3 — never ignore a complexity signal upward.
    # -------------------------------------------------------------------
    priority_floor = {"low": 1, "medium": 2}
    min_tier = priority_floor.get(priority, 1)
    final_tier = max(analyzed_tier, min_tier)

    # Get model for the final tier
    tier_models = registry.get_by_tier(final_tier)
    if not tier_models:
        raise ValueError(f"No models found for tier {final_tier}")

    return {
        "model_name": tier_models[0].name,
        "optimized_prompt": optimized_prompt,
        "routing_reason": analysis["reason"] + (
            f" Prompt optimized: {tokens_saved} tokens saved "
            f"({percent_saved}%)."
        ),
        "tokens_saved": tokens_saved,
        "percent_saved": percent_saved
    }


@app.post("/llm/request", response_model=LLMResponse)
async def process_request(req: LLMRequest) -> LLMResponse:
    """
    Main endpoint. Optimizes prompt, routes to best model, returns response.

    Example request body:
    {
        "prompt": "Could you please analyze the financial risks of expanding into Europe?",
        "team_id": "strategy",
        "feature_name": "risk_analysis",
        "priority": "low"
    }

    What happens:
        1. Optimizer removes "Could you please" → saves tokens
        2. Analyzer sees "analyze" + "financial" → risk override → Tier 3
        3. Claude Opus answers the question
        4. Response includes routing_reason, tokens_saved, cost
    """
    try:
        # Route the request (optimize + analyze + pick model)
        routing = _route_request(
            prompt=req.prompt,
            priority=req.priority,
            preferred_model=req.preferred_model
        )

        # Call Claude with the OPTIMIZED prompt
        response = anthropic_provider.call(
            model_name=routing["model_name"],
            prompt=routing["optimized_prompt"],
            routing_info={
                "routing_reason": routing["routing_reason"],
                "tokens_saved": routing["tokens_saved"],
                "percent_saved": routing["percent_saved"]
            }
        )

        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


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
        "version": "2.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)