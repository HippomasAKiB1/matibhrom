"""
HuggingFace transformers model adapter for Matibhrom - fallback for local models.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    pipeline = None
    AutoModelForCausalLM = None
    AutoTokenizer = None

from .base import ModelAdapter, GenerationResult

class HFAdapter(ModelAdapter):
    def __init__(self, model_id: str, params: dict):
        super().__init__(model_id, params)
        self.path = params.get("path", model_id)
        self.temperature = params.get("temperature", 0.0)
        self.max_tokens = params.get("max_tokens", 512)
        self.top_p = params.get("top_p", 1.0)
        self.seed = params.get("seed", 42)
        self._pipe = None

    def _load_pipeline(self):
        """Load the transformers pipeline."""
        if not HF_AVAILABLE:
            raise ImportError(
                "transformers is not installed. Install with: pip install transformers"
            )

        if self._pipe is None:
            logger.info(f"Loading HF pipeline for {self.path}")
            self._pipe = pipeline(
                "text-generation",
                model=self.path,
                torch_dtype="auto",
                device_map="auto",
                trust_remote_code=True
            )
        return self._pipe

    def generate(self, prompt: str) -> GenerationResult:
        """Generate a single response using HF transformers."""
        pipe = self._load_pipeline()

        result = pipe(
            prompt,
            max_new_tokens=self.max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            do_sample=self.temperature > 0.0,
            truncation=True
        )

        text = result[0]["generated_text"]
        # Remove the prompt part if included
        if text.startswith(prompt):
            text = text[len(prompt):]

        return GenerationResult(
            text=text.strip(),
            model_version=pipe.model.config._name_or_path,
            prompt_tokens=0,  # Not directly available without tokenizer call
            response_tokens=len(text.split()),
            latency_ms=None,
            cost_usd=None
        )

    def generate_batch(self, prompts: list[str]) -> list[GenerationResult]:
        """Generate responses for multiple prompts."""
        return [self.generate(p) for p in prompts]

    def unload(self) -> None:
        """Free the HF pipeline."""
        if self._pipe is not None:
            del self._pipe
            self._pipe = None