"""
Base model adapters for Matibhrom.
"""

from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Any
@dataclass
class GenerationResult:
    text: str
    model_version: str
    prompt_tokens: int
    response_tokens: int
    latency_ms: int | None = None
    cost_usd: float | None = None
    error: str | None = None
class ModelAdapter(ABC):
    def __init__(self, model_id: str, params: dict):
        self.model_id = model_id
        self.params = params

    @abstractmethod
    def generate(self, prompt: str) -> GenerationResult:
        """Generate a single response from the model."""
        pass

    def generate_batch(self, prompts: list[str]) -> list[GenerationResult]:
        """Generate responses for multiple prompts."""
        return [self.generate(p) for p in prompts]

    def unload(self) -> None:
        """Unload model from memory if applicable."""
        return None