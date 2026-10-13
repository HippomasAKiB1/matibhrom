"""
LiteLLM model adapter for Matibhrom - supports OpenAI, Anthropic, Google, and other APIs.
"""

import logging
import os
import time
from typing import Any

from dotenv import load_dotenv
load_dotenv()

import litellm
from .base import ModelAdapter, GenerationResult

logger = logging.getLogger(__name__)

class LiteLLMAdapter(ModelAdapter):
    def __init__(self, model_id: str, params: dict):
        super().__init__(model_id, params)
        self.model = params.get("model", model_id)
        self.temperature = params.get("temperature", 0.0)
        self.max_tokens = params.get("max_tokens", 512)
        self.seed = params.get("seed", 42)
        self.top_p = params.get("top_p", 1.0)

        # Retry configuration
        self.max_retries = 3
        self.base_backoff = 2.0

    def generate(self, prompt: str) -> GenerationResult:
        """Generate a single response using LiteLLM."""
        last_error = None

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()

                extra_kwargs = {}
                if self.model.startswith("openrouter/") and os.environ.get("OPENROUTER_API_KEY"):
                    extra_kwargs["api_key"] = os.environ.get("OPENROUTER_API_KEY")

                response = litellm.completion(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    top_p=self.top_p,
                    seed=self.seed if self.seed is not None else None,
                    **extra_kwargs,
                )

                latency_ms = int((time.time() - start_time) * 1000)

                # Extract response text
                msg = response.choices[0].message
                text = msg.content or ""
                if not text and hasattr(msg, "reasoning_content") and msg.reasoning_content:
                    text = msg.reasoning_content

                # Get model version from response
                model_version = getattr(response, "model", self.model)

                # Get token counts
                prompt_tokens = response.usage.prompt_tokens if response.usage else 0
                response_tokens = response.usage.completion_tokens if response.usage else 0

                # Get cost if available
                cost_usd = None
                if hasattr(response, "_hidden_params") and "response_cost" in response._hidden_params:
                    cost_usd = response._hidden_params["response_cost"]
                elif hasattr(response, "cost"):
                    cost_usd = response.cost

                logger.info(f"API call to {self.model} - {latency_ms}ms, {prompt_tokens}+{response_tokens} tokens, cost=${cost_usd}")

                return GenerationResult(
                    text=text,
                    model_version=model_version,
                    prompt_tokens=prompt_tokens,
                    response_tokens=response_tokens,
                    latency_ms=latency_ms,
                    cost_usd=cost_usd
                )

            except (litellm.RateLimitError, litellm.APITimeoutError, litellm.APIConnectionError, litellm.ServiceUnavailableError) as e:
                last_error = e
                wait_time = self.base_backoff * (2 ** attempt)
                logger.warning(f"Transient error ({type(e).__name__}), waiting {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                time.sleep(wait_time)

            except Exception as e:
                err_str = str(e).lower()
                if any(x in err_str for x in ["429", "503", "rate-limit", "rate limit", "overloaded", "temporarily"]):
                    last_error = e
                    wait_time = self.base_backoff * (2 ** attempt)
                    logger.warning(f"Upstream rate/capacity limit, waiting {wait_time}s (attempt {attempt + 1}/{self.max_retries}): {e}")
                    time.sleep(wait_time)
                else:
                    last_error = e
                    logger.error(f"Unexpected error for {self.model}: {e}")
                    break

        # All retries failed
        error_msg = str(last_error) if last_error else "Unknown error"
        logger.error(f"All retries failed for {self.model}: {error_msg}")

        return GenerationResult(
            text="",
            model_version=self.model,
            prompt_tokens=0,
            response_tokens=0,
            latency_ms=0,
            cost_usd=0.0,
            error=error_msg
        )

    def generate_batch(self, prompts: list[str]) -> list[GenerationResult]:
        """Generate responses for multiple prompts."""
        # LiteLLM supports batch via completion with multiple messages
        # But for simplicity and to track individual costs, we do sequential
        return [self.generate(p) for p in prompts]