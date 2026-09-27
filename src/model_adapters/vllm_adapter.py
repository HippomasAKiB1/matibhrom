"""
VLLM model adapter for Matibhrom - local high-throughput generation.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from vllm import LLM, SamplingParams
    VLLM_AVAILABLE = True
except ImportError:
    VLLM_AVAILABLE = False
    LLM = None
    SamplingParams = None

from .base import ModelAdapter, GenerationResult

class VLLMAdapter(ModelAdapter):
    def __init__(self, model_id: str, params: dict):
        super().__init__(model_id, params)
        self.path = params.get("path", model_id)
        self.temperature = params.get("temperature", 0.0)
        self.max_tokens = params.get("max_tokens", 512)
        self.top_p = params.get("top_p", 1.0)
        self.seed = params.get("seed", 42)
        self.deterministic = params.get("deterministic", False)
        self._engine = None

    def _load_engine(self):
        """Load the vLLM engine."""
        if not VLLM_AVAILABLE:
            raise ImportError(
                "vLLM is not installed. Install with: pip install vllm==0.6.3.post1"
            )

        if self._engine is None:
            logger.info(f"Loading vLLM engine for {self.path}")
            self._engine = LLM(
                model=self.path,
                enforce_eager=self.deterministic,
                trust_remote_code=True
            )
        return self._engine

    def generate(self, prompt: str) -> GenerationResult:
        """Generate a single response using vLLM."""
        engine = self._load_engine()

        sampling_params = SamplingParams(
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            top_p=self.top_p,
            seed=self.seed,
            use_beam_search=False
        )

        outputs = engine.generate(prompt, sampling_params)

        result = outputs[0].outputs[0]

        return GenerationResult(
            text=result.text,
            model_version=engine.model_executor.driver_worker.model_runner.model,
            prompt_tokens=outputs[0].prompt_token_ids,
            response_tokens=len(result.token_ids),
            latency_ms=int(outputs[0].outputs[0].cumulative_logprob * 1000) if outputs[0].outputs[0].cumulative_logprob else None,
            cost_usd=None
        )

    def generate_batch(self, prompts: list[str]) -> list[GenerationResult]:
        """Generate responses for multiple prompts using vLLM batch."""
        engine = self._load_engine()

        sampling_params = SamplingParams(
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            top_p=self.top_p,
            seed=self.seed,
            use_beam_search=False
        )

        outputs = engine.generate(prompts, sampling_params)

        results = []
        for i, output in enumerate(outputs):
            result = output.outputs[0]
            results.append(GenerationResult(
                text=result.text,
                model_version=engine.model_executor.driver_worker.model_runner.model,
                prompt_tokens=output.prompt_token_ids,
                response_tokens=len(result.token_ids),
                latency_ms=None,
                cost_usd=None
            ))

        return results

    def unload(self) -> None:
        """Free the vLLM engine."""
        if self._engine is not None:
            del self._engine
            self._engine = None