from pathlib import Path

import pytest

from src.budget import BudgetExceededError, check_budget, estimate_cost
from src.prompts.builder import PromptBuilder
from src.runner.cache import GenerationCache
from src.runner.generate import GenerationRunner
from src.schema import Item
from src.validate_data import validate_artifact


def test_dummy_benchmark_valid():
    errors = validate_artifact(
        Path("data/dummy/items.jsonl"),
        Path("data/dummy/evidence.jsonl"),
        Path("data/dummy/corpus.jsonl"),
        min_corpus_passages=10,
    )
    assert errors == []


def test_budget_guard_and_estimation():
    pricing = {"dummy": {"input_per_million": 1.0, "output_per_million": 2.0}}
    assert estimate_cost("dummy", 500_000, 250_000, pricing) == pytest.approx(1.0)

    check_budget(Path("configs/budget.yaml"), 1.0)
    with pytest.raises(BudgetExceededError):
        check_budget(Path("configs/budget.yaml"), 9999.0)


def test_prompt_builder_builds_all_conditions():
    builder = PromptBuilder("configs/prompts")
    item = Item.model_validate(
        {
            "schema_version": "1.0.0",
            "item_id": "gen_0001",
            "domain": "general",
            "question_bn": "বাংলাদেশের জাতীয় ফুল কোনটি?",
            "question_banglish": "Bangladesh er jatiyo phul konti?",
            "gold_answer": "শাপলা",
            "evidence_id": "ev_gen_0001",
            "answer_type": "entity",
            "risk_tag": "normal",
            "split": "dev",
            "group_key": None,
        }
    )

    c0_prompt, key = builder.build_prompt(item, "bn", "C0")
    assert "প্রশ্ন: বাংলাদেশের জাতীয় ফুল কোনটি?" in c0_prompt
    assert key == "C0_bn"

    evidence = "বাংলাদেশের জাতীয় ফুল শাপলা।"
    c1_prompt, _ = builder.build_prompt(item, "banglish", "C1", evidence=evidence)
    assert "Proman: বাংলাদেশের জাতীয় ফুল শাপলা।" in c1_prompt

    c2_prompt, _ = builder.build_prompt(
        item,
        "bn",
        "C2",
        retrieved_context="[Passage 1] বাংলাদেশের জাতীয় ফুল শাপলা।",
    )
    assert "[Passage 1]" in c2_prompt

    c3_prompt, _ = builder.build_prompt(
        item,
        "bn",
        "C3",
        retrieved_context="[Passage 1] বাংলাদেশের জাতীয় ফুল শাপলা।",
    )
    assert builder.get_abstention_phrase() in c3_prompt


def test_generation_runner_emits_dummy_generations(tmp_path):
    item = Item.model_validate(
        {
            "schema_version": "1.0.0",
            "item_id": "gen_0001",
            "domain": "general",
            "question_bn": "বাংলাদেশের জাতীয় ফুল কোনটি?",
            "question_banglish": "Bangladesh er jatiyo phul konti?",
            "gold_answer": "শাপলা",
            "evidence_id": "ev_gen_0001",
            "answer_type": "entity",
            "risk_tag": "normal",
            "split": "dev",
            "group_key": None,
        }
    )
    builder = PromptBuilder("configs/prompts")
    cache = GenerationCache(tmp_path / "cache.db")
    runner = GenerationRunner(
        run_id="smoke_run",
        items=[item],
        languages=["bn"],
        conditions=["C0"],
        models=[{"id": "dummy", "adapter": "dummy", "params": {"response": "ডামি উত্তর।"}}],
        prompt_builder=builder,
        cache=cache,
        output_dir=tmp_path,
    )

    generations = runner.generate_all()
    assert len(generations) == 1
    assert generations[0].item_id == "gen_0001"
    assert generations[0].condition == "C0"
    assert generations[0].model_id == "dummy"
    assert generations[0].response == "ডামি উত্তর।"
