from abc import ABC, abstractmethod
from schemas.request import LLMResponse


class BaseProvider(ABC):
    """
    The rulebook that every LLM provider must follow.

    ABC stands for Abstract Base Class. It lets us write rules
    that child classes MUST implement. If a child class forgets
    to implement a required method, Python raises an error immediately.

    Think of it like a job contract:
    "If you want to work here as a provider, you MUST be able
    to accept a prompt and return an LLMResponse. How you do it
    internally is your business."

    This means main.py never needs to know whether it is talking
    to Anthropic, OpenAI, or any other provider. It just calls
    .call() and gets back an LLMResponse every time.
    """

    def __init__(self, api_key: str):
        """
        Store the API key so all methods in this class can use it.

        Args:
            api_key: The authentication key for the provider's API.
        """
        self.api_key = api_key

    @abstractmethod
    def call(self, model_name: str, prompt: str, routing_info: dict) -> LLMResponse:
        """
        Send a prompt to the model and return a standardized response.

        This method is marked @abstractmethod which means:
        - BaseProvider itself does NOT implement it (notice no code, just pass)
        - Every class that inherits from BaseProvider MUST implement it
        - If they forget, Python throws a TypeError immediately

        Args:
            model_name   : Which model to use. Must exist in registry.
            prompt       : The optimized prompt text to send.
            routing_info : Dict containing routing_reason, tokens_saved,
                          percent_saved from the optimizer and analyzer.

        Returns:
            LLMResponse: Standardized response with text, cost, tokens, latency.
        """
        pass