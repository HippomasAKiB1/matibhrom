"""
Regression tests for failure injection scenarios:
1. Invalid API key (raises error, no cache write, lock released)
2. Model empty string (raises error, no cache write, lock released)
3. Non-JSON in pre-labeling (handled cleanly, retry attempted, fails gracefully)
4. Network timeout (raises error, no cache write, lock released)
"""

import json
from pathlib import Path
import pytest

from src.schema import Item
from src.prompts.builder import PromptBuilder
from src.runner.cache import GenerationCache
from src.runner.generate import GenerationRunner
from src.model_adapters.base import ModelAdapter, GenerationResult
import src.model_adapters as model_adapters
from src.annotation.prelabel import prelabel_one, run_prelabeling


class FailingMockAdapter(ModelAdapter):
    """Adapter that simulates injected failures."""

    def __init__(self, model_id: str, params: dict):
        super().__init__(model_id, params)
        self.mode = params.get("failure_mode", "none")

    def generate(self, prompt: str) -> GenerationResult:
        if self.mode == "invalid_api_key":
            return GenerationResult(
                text="",
                model_version=self.model_id,
                prompt_tokens=0,
                response_tokens=0,
                latency_ms=10,
                cost_usd=0.0,
                error="AuthenticationError: 401 Invalid API key provided",
            )
        elif self.mode == "empty_string":
            return GenerationResult(
                text="",
                model_version=self.model_id,
                prompt_tokens=10,
                response_tokens=0,
                latency_ms=15,
                cost_usd=0.0,
                error=None,
            )
        elif self.mode == "network_timeout":
            return GenerationResult(
                text="",
                model_version=self.model_id,
                prompt_tokens=0,
                response_tokens=0,
                latency_ms=5000,
                cost_usd=0.0,
                error="APITimeoutError: Request timed out after 30s",
            )
        elif self.mode == "valid":
            return GenerationResult(
                text="ঢাকা বাংলাদেশের রাজধানী।",
                model_version=self.model_id,
                prompt_tokens=10,
                response_tokens=10,
                latency_ms=50,
                cost_usd=0.0,
            )
        return GenerationResult(text="", model_version=self.model_id)


def _make_dummy_item() -> Item:
    return Item(
        item_id="test_fail_001",
        domain="general",
        question_bn="বাংলাদেশের রাজধানী কী?",
        question_banglish="Bangladesher rajdhani ki?",
        gold_answer="ঢাকা",
        evidence_id="ev_001",
        answer_type="entity",
        risk_tag="normal",
        split="dev",
        group_key="g1",
    )


@pytest.fixture(autouse=True)
def register_mock_adapter(monkeypatch):
    monkeypatch.setitem(model_adapters._ADAPTER_CACHE, "mock_fail", FailingMockAdapter)


PROMPTS_DIR = Path("configs/prompts")


def test_invalid_api_key_failure_no_cache_write(tmp_path):
    run_id = "test_invalid_api_key"
    cache_path = tmp_path / "cache.db"
    cache = GenerationCache(str(cache_path))
    prompt_builder = PromptBuilder(prompt_dir=PROMPTS_DIR)

    model_config = {
        "id": "mock_model",
        "adapter": "mock_fail",
        "params": {"failure_mode": "invalid_api_key"},
    }

    runner = GenerationRunner(
        run_id=run_id,
        items=[_make_dummy_item()],
        languages=["bn"],
        conditions=["C0"],
        models=[model_config],
        prompt_builder=prompt_builder,
        cache=cache,
        output_dir=tmp_path,
        workers=1,
    )

    with pytest.raises(RuntimeError) as exc_info:
        runner.generate_all()

    assert "AuthenticationError: 401" in str(exc_info.value)
    # Check that no generation was written to generations.jsonl
    assert not runner.generations_path.exists()
    # Check that cache is empty
    assert cache.count() == 0
    # Check that lock file was cleaned up
    assert list(runner.locks_dir.glob("*.lock")) == []


def test_empty_string_failure_no_cache_write(tmp_path):
    run_id = "test_empty_string"
    cache_path = tmp_path / "cache.db"
    cache = GenerationCache(str(cache_path))
    prompt_builder = PromptBuilder(prompt_dir=PROMPTS_DIR)

    model_config = {
        "id": "mock_model",
        "adapter": "mock_fail",
        "params": {"failure_mode": "empty_string"},
    }

    runner = GenerationRunner(
        run_id=run_id,
        items=[_make_dummy_item()],
        languages=["bn"],
        conditions=["C0"],
        models=[model_config],
        prompt_builder=prompt_builder,
        cache=cache,
        output_dir=tmp_path,
        workers=1,
    )

    with pytest.raises(RuntimeError) as exc_info:
        runner.generate_all()

    assert "empty completion" in str(exc_info.value).lower()
    assert not runner.generations_path.exists()
    assert cache.count() == 0
    assert list(runner.locks_dir.glob("*.lock")) == []


def test_network_timeout_failure_no_cache_write(tmp_path):
    run_id = "test_network_timeout"
    cache_path = tmp_path / "cache.db"
    cache = GenerationCache(str(cache_path))
    prompt_builder = PromptBuilder(prompt_dir=PROMPTS_DIR)

    model_config = {
        "id": "mock_model",
        "adapter": "mock_fail",
        "params": {"failure_mode": "network_timeout"},
    }

    runner = GenerationRunner(
        run_id=run_id,
        items=[_make_dummy_item()],
        languages=["bn"],
        conditions=["C0"],
        models=[model_config],
        prompt_builder=prompt_builder,
        cache=cache,
        output_dir=tmp_path,
        workers=1,
    )

    with pytest.raises(RuntimeError) as exc_info:
        runner.generate_all()

    assert "APITimeoutError" in str(exc_info.value)
    assert not runner.generations_path.exists()
    assert cache.count() == 0
    assert list(runner.locks_dir.glob("*.lock")) == []


class PrelabelMockAdapter:
    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.calls = 0

    def generate(self, prompt: str) -> GenerationResult:
        self.calls += 1
        resp = self.responses.pop(0) if self.responses else ""
        return GenerationResult(
            text=resp,
            model_version="mock_prelabel",
            prompt_tokens=10,
            response_tokens=10,
        )


def test_prelabel_non_json_retry_and_graceful_failure():
    item = {
        "item_id": "item_1",
        "question_bn": "প্রশ্ন",
        "question_banglish": "proshno",
        "gold_answer": "উত্তর",
        "evidence_text": "প্রমাণ",
    }
    gen = {
        "generation_id": "gen_1",
        "language": "bn",
        "response": "মডেলের উত্তর",
    }

    # Case 1: Initial call is non-JSON, but retry succeeds
    valid_json = json.dumps({
        "correctness": "correct",
        "hallucination": "no",
        "error_type": "none",
        "abstention_status": "none",
    })
    adapter_recovers = PrelabelMockAdapter([
        "আমি নিশ্চিত নই, তবে এটি ভালো উত্তর।",  # Invalid non-JSON
        f"```json\n{valid_json}\n```",          # Retry succeeds
    ])

    res = prelabel_one(adapter_recovers, item, gen)
    assert res is not None
    assert res["correctness"] == "correct"
    assert adapter_recovers.calls == 2

    # Case 2: Both initial and retry fail -> returns None cleanly without crashing
    adapter_fails = PrelabelMockAdapter([
        "এটি সম্পূর্ণ অর্থহীন লেখা।",
        "এখনো কোনো JSON তৈরি করতে পারছি না।",
    ])
    res_fail = prelabel_one(adapter_fails, item, gen)
    assert res_fail is None
    assert adapter_fails.calls == 2
