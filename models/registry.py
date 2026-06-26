from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Model:
    """
    Represents one available Claude model.

    Think of each Model as one dish on a restaurant menu.
    It has a name, a price, a quality rating, and a description
    of what it is best suited for.

    Fields:
        name                      : The exact model ID used in API calls.
        provider                  : Always "anthropic" for this project.
        quality_tier              : 1 = cheapest, 2 = balanced, 3 = best.
        input_cost_per_1k_tokens  : Price in USD per 1,000 input tokens.
        output_cost_per_1k_tokens : Price in USD per 1,000 output tokens.
        max_context_length        : Maximum tokens this model can accept.
        description               : When to use this model.
    """
    name: str
    provider: str
    quality_tier: int
    input_cost_per_1k_tokens: float
    output_cost_per_1k_tokens: float
    max_context_length: int
    description: str


class ModelRegistry:
    """
    The central menu of all available models.

    This is a singleton — one shared instance used by the whole app.
    The router reads from this to decide which model to use.
    The cost tracker reads from this to calculate prices.

    To add a new model: add it to self.models in __init__.
    No other file needs to change.
    """

    def __init__(self):
        self.models: Dict[str, Model] = {

            # -----------------------------------------------------------
            # TIER 1 — Cheapest and fastest.
            # Best for: simple Q&A, extraction, formatting, translation.
            # -----------------------------------------------------------
            "claude-haiku-4-5": Model(
                name="claude-haiku-4-5",
                provider="anthropic",
                quality_tier=1,
                input_cost_per_1k_tokens=0.00008,
                output_cost_per_1k_tokens=0.00025,
                max_context_length=200000,
                description="Cheapest and fastest. Simple tasks only."
            ),

            # -----------------------------------------------------------
            # TIER 2 — Balanced cost and quality.
            # Best for: summarization, drafting, classification.
            # -----------------------------------------------------------
            "claude-sonnet-4-6": Model(
                name="claude-sonnet-4-6",
                provider="anthropic",
                quality_tier=2,
                input_cost_per_1k_tokens=0.003,
                output_cost_per_1k_tokens=0.015,
                max_context_length=200000,
                description="Balanced model. Good for most tasks."
            ),

            # -----------------------------------------------------------
            # TIER 3 — Best quality. Use only when accuracy is critical.
            # Best for: legal, medical, financial, complex reasoning.
            # -----------------------------------------------------------
            "claude-opus-4-6": Model(
                name="claude-opus-4-6",
                provider="anthropic",
                quality_tier=3,
                input_cost_per_1k_tokens=0.015,
                output_cost_per_1k_tokens=0.075,
                max_context_length=200000,
                description="Most capable. High-stakes and complex tasks."
            ),
        }

    def get_model(self, name: str) -> Model:
        """
        Fetch a model by its exact name.
        Raises a clear error if the model does not exist.

        Args:
            name: The model name. Example: "claude-haiku-4-5"

        Returns:
            Model: The matching Model object.
        """
        if name not in self.models:
            available = list(self.models.keys())
            raise ValueError(
                f"Model '{name}' not found. "
                f"Available models: {available}"
            )
        return self.models[name]

    def get_by_tier(self, tier: int) -> List[Model]:
        """
        Return all models that match a specific quality tier.

        Args:
            tier: 1, 2, or 3.

        Returns:
            List[Model]: All models at that tier.
        """
        return [
            model for model in self.models.values()
            if model.quality_tier == tier
        ]

    def list_all(self) -> Dict[str, Model]:
        """Return every model in the registry."""
        return self.models


# -------------------------------------------------------------------
# One shared instance for the whole application.
# Every file that needs the registry imports THIS object.
# This means there is always exactly one menu — no duplicates.
# -------------------------------------------------------------------
registry = ModelRegistry()