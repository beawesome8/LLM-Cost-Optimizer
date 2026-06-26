import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from schemas.request import LLMRequest, LLMResponse
from providers.anthropic_adapter import AnthropicProvider
from models.registry import registry

load_dotenv()

# -----------------------------------------------------------------------
# Create the FastAPI application.
# FastAPI auto-generates interactive documentation at /docs
# The moment the server starts, go to http://localhost:8000/docs
# and you can test every endpoint from your browser.
# -----------------------------------------------------------------------
app = FastAPI(
    title="LLM Cost Optimizer",
    description=(
        "A gateway that optimizes prompts and routes requests "
        "to the most cost-effective Claude model automatically."
    ),
    version="1.0.0"
)

# -----------------------------------------------------------------------
# Create ONE shared provider instance.
# We do this at startup, not inside each request handler.
# Reason: creating it inside the handler would re-read the .env file
# and re-initialize the provider on every single request — wasteful.
# -----------------------------------------------------------------------
anthropic_provider = AnthropicProvider()


@app.post("/llm/request", response_model=LLMResponse)
async def process_request(req: LLMRequest) -> LLMResponse:
    """
    Main endpoint. Receives a prompt and returns Claude's response.

    Phase 1 implementation: basic routing by priority only.
    Phase 2 will replace select_model() with the full
    complexity analyzer and prompt optimizer.

    Example request body:
    {
        "prompt": "What is the capital of France?",
        "team_id": "marketing",
        "feature_name": "qa_bot",
        "priority": "low"
    }

    Returns:
        LLMResponse with text, model used, cost, tokens, and routing info.
    """
    try:
        # Phase 1: Simple routing — priority maps directly to tier
        model_name = _select_model_by_priority(
            req.priority,
            req.preferred_model
        )

        # Routing info placeholder — Phase 2 will fill this properly
        routing_info = {
            "routing_reason": f"Priority '{req.priority}' → direct tier mapping.",
            "tokens_saved": 0,
            "percent_saved": 0.0
        }

        # Call Claude
        response = anthropic_provider.call(
            model_name,
            req.prompt,
            routing_info
        )

        return response

    except ValueError as e:
        # Bad input — wrong model name, bad priority, etc.
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Anthropic API error — bad key, network issue, rate limit
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        # Anything else unexpected
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


def _select_model_by_priority(
    priority: str,
    preferred_model: str | None
) -> str:
    """
    Phase 1 routing: map priority directly to a model tier.

    This is intentionally simple. Phase 2 replaces this with
    the full complexity analyzer.

    Priority → Tier → Model:
        "low"    → Tier 1 → claude-haiku   (cheapest)
        "medium" → Tier 2 → claude-sonnet  (balanced)
        "high"   → Tier 3 → claude-opus    (best)

    Args:
        priority       : "low", "medium", or "high"
        preferred_model: If set, use this model directly.

    Returns:
        str: The model name to use.
    """
    # User override — skip routing entirely
    if preferred_model:
        return preferred_model

    tier_map = {"low": 1, "medium": 2, "high": 3}
    tier = tier_map.get(priority, 2)  # Default to tier 2 if unknown

    models_in_tier = registry.get_by_tier(tier)
    if not models_in_tier:
        raise ValueError(
            f"No models available for priority '{priority}' (tier {tier})"
        )

    return models_in_tier[0].name


@app.get("/models")
def list_models():
    """
    Returns every model in the registry with its pricing and tier info.
    Visit http://localhost:8000/models in your browser to see this.
    """
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
    """
    Confirms the server is running.
    Always the first thing to test after starting the server.
    """
    return {
        "status": "ok",
        "service": "LLM Cost Optimizer",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    # host="0.0.0.0" means accept connections from any address
    # port=8000 is the standard port for local development
    uvicorn.run(app, host="0.0.0.0", port=8000)