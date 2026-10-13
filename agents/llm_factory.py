"""Deterministic demonstration responder; no external model connections."""
from .base import PHIGuard


class MockLLM:
    def __init__(self, system_name: str = "Qt Drug Tisdale Risk Score"):
        self.system_name = system_name

    def invoke(self, prompt: str) -> str:
        PHIGuard.assert_no_phi(prompt)
        return (
            "Demonstration response only. No model inference, evidence review, "
            "clinical validation, or external request was performed."
        )


class LLMFactory:
    """Only the offline mock provider is implemented."""

    @staticmethod
    def create(provider: str = "mock", system_name: str = "Qt Drug Tisdale Risk Score"):
        if str(provider).lower() in ("mock", "deterministic", "test"):
            return MockLLM(system_name)
        raise ValueError(
            f"Unsupported model provider {provider!r}: this repository only implements the offline mock."
        )
