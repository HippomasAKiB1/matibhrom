"""
Dummy model adapter for Matibhrom - returns fixed responses for testing.
"""

import time
from typing import Any

from .base import ModelAdapter, GenerationResult
class DummyAdapter(ModelAdapter):
    def generate(self, prompt: str) -> GenerationResult:
        """Return a fixed response from params.response."""
        # Simulate some processing time
        time.sleep(0.01)

        response_text = self.params.get("response", "ডামি উত্তর।")

        # Approximate token count by whitespace splitting
        prompt_tokens = len(prompt.split())
        response_tokens = len(response_text.split())

        return GenerationResult(
            text=response_text,
            model_version="dummy-1.0",
            prompt_tokens=prompt_tokens,
            response_tokens=response_tokens,
            latency_ms=10,
            cost_usd=0.0
        )