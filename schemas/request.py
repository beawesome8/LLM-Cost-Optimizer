from pydantic import BaseModel
from typing import Optional


class LLMRequest(BaseModel):
    """
    The standard request format for the LLM Cost Optimizer.

    Every request coming into the system must match this shape.
    Pydantic validates this automatically — if a field is missing
    or the wrong type, it rejects the request immediately with
    a clear error message.

    Fields:
        prompt        : The actual question or instruction for Claude.
        team_id       : Which team is making this request.
                        Used for budget tracking. Example: "marketing"
        feature_name  : Which product feature triggered this request.
                        Used for cost breakdown. Example: "email_writer"
        priority      : How important is this request?
                        "low"    → use cheapest model possible
                        "medium" → use balanced model
                        "high"   → use best model, cost is secondary
        preferred_model: Optional. If set, skip routing and use this
                        specific model directly.
    """
    prompt: str
    team_id: str
    feature_name: str
    priority: str = "medium"
    preferred_model: Optional[str] = None


class LLMResponse(BaseModel):
    """
    The standard response format returned by the gateway.

    Every provider (Anthropic today, others tomorrow) must return
    data in this exact shape. This means the rest of your app
    never needs to know which provider was used.

    Fields:
        text          : The actual response text from Claude.
        model_used    : Which Claude model answered this request.
        tokens_input  : How many tokens were in your prompt.
        tokens_output : How many tokens Claude generated.
        cost          : Total cost in USD for this request.
        latency_ms    : How long Claude took to respond (milliseconds).
        routing_reason: Why this model was chosen. Useful for debugging.
        tokens_saved  : How many tokens the optimizer removed.
        percent_saved : Percentage of tokens saved by optimization.
    """
    text: str
    model_used: str
    tokens_input: int
    tokens_output: int
    cost: float
    latency_ms: float
    routing_reason: str
    tokens_saved: int
    percent_saved: float