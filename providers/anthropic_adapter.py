import os
import requests
from time import time
from dotenv import load_dotenv
from schemas.request import LLMResponse
from providers.base import BaseProvider
from models.registry import registry

load_dotenv()


class AnthropicProvider(BaseProvider):
    """
    The Anthropic-specific implementation of BaseProvider.

    This class knows exactly how to talk to Anthropic's API.
    It handles the HTTP request format, parses the response,
    calculates the cost, and returns everything as LLMResponse.

    The rest of the app does not need to know any of this.
    It just calls .call() and gets back a clean LLMResponse.
    """

    def __init__(self, api_key: str | None = None):
        """
        Initialize the Anthropic provider.

        Tries to get the API key in this order:
        1. From the api_key parameter (if passed directly)
        2. From the ANTHROPIC_API_KEY environment variable (.env file)

        If neither exists, raises a clear error immediately.
        Better to fail at startup than fail silently mid-request.

        Args:
            api_key: Optional API key override.
        """
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set.\n"
                "Create a .env file and add:\n"
                "ANTHROPIC_API_KEY=your_key_here"
            )
        super().__init__(api_key)
        self.base_url = "https://api.anthropic.com"
        self.api_version = "2023-06-01"

    def call(
        self,
        model_name: str,
        prompt: str,
        routing_info: dict
    ) -> LLMResponse:
        """
        Send an optimized prompt to Claude and return a standardized response.

        Steps:
            1. Look up model in registry (need price for cost calculation)
            2. Build HTTP request headers (authentication + format)
            3. Build HTTP request body (model, prompt, settings)
            4. Send request to Anthropic API and measure latency
            5. Parse the response JSON
            6. Calculate cost from token counts and model pricing
            7. Return everything as LLMResponse

        Args:
            model_name   : Claude model to use. Example: "claude-haiku-4-5"
            prompt       : The already-optimized prompt text.
            routing_info : Contains routing_reason, tokens_saved, percent_saved.

        Returns:
            LLMResponse: Full standardized response with cost and metadata.
        """

        # Step 1: Get model pricing from the registry
        model = registry.get_model(model_name)

        # Step 2: Build headers
        # Headers are metadata sent alongside the request.
        # Like the outside of an envelope — who it is from, what format it is.
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "content-type": "application/json"
        }

        # Step 3: Build the request body
        # This is the actual content — the letter inside the envelope.
        payload = {
            "model": model_name,
            "max_tokens": 1024,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        # Step 4: Send the request and measure how long it takes
        start_time = time()
        try:
            response = requests.post(
                f"{self.base_url}/v1/messages",
                headers=headers,
                json=payload,
                timeout=30
            )
            # Raise an error if status code is 4xx or 5xx
            response.raise_for_status()

        except requests.exceptions.HTTPError as e:
            raise RuntimeError(
                f"Anthropic API HTTP error: {e} | "
                f"Response: {response.text}"
            )
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Anthropic connection error: {e}")

        # Convert seconds to milliseconds
        latency_ms = (time() - start_time) * 1000

        # Step 5: Parse the raw JSON response from Anthropic
        data = response.json()
        tokens_input = data["usage"]["input_tokens"]
        tokens_output = data["usage"]["output_tokens"]
        text = data["content"][0]["text"]

        # Step 6: Calculate cost
        # Formula: (tokens used / 1000) × price per 1000 tokens
        # We divide by 1000 because Anthropic prices are per 1K tokens
        cost_input = (tokens_input / 1000) * model.input_cost_per_1k_tokens
        cost_output = (tokens_output / 1000) * model.output_cost_per_1k_tokens
        total_cost = cost_input + cost_output

        # Step 7: Return everything in our standard format
        return LLMResponse(
            text=text,
            model_used=model_name,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost=round(total_cost, 8),
            latency_ms=round(latency_ms, 2),
            routing_reason=routing_info.get("routing_reason", ""),
            tokens_saved=routing_info.get("tokens_saved", 0),
            percent_saved=routing_info.get("percent_saved", 0.0)
        )