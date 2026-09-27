from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.annotation.auth import AuthError, authenticate, assert_safe_to_disable_auth
from src.annotation.prelabel import _extract_json
from src.annotation.store import AnnotationStore
from src.prompts.builder import PromptBuilder
from src.runner.cache import GenerationCache
from src.runner.generate import GenerationRunner
from src.schema import Annotation, Item


def _make_item(item_id="gen_0001", evidence_id="ev_gen_0001"):
    return Item.model_validate(
        {
            "schema_version": "1.0.0",
            "item_id": item_id,
            "domain": "general",
            "question_bn": "বাংলাদেশের জাতীয় ফুল কোনটি?",
            "question_banglish": "Bangladesh er jatiyo phul konti?",
            "gold_answer": "শাপলা",
            "evidence_id": evidence_id,
            "answer_type": "entity",
            "risk_tag": "normal",
            "split": "dev",
            "group_key": None,
        }
    )


class FakeRetriever:
    """Minimal retriever double: always returns the gold evidence plus one
    distractor passage, so evidence_ids_used dedup logic (§9.10) can be
    exercised without FAISS/embeddings."""

    top_k = 3
    index_version = "idx_test"
    corpus_version = "corpus_test"

    def retrieve_for_item(self, item_id, question, evidence_id):
        retrieved = [
            {"rank": 1, "passage_id": evidence_id, "evidence_id": evidence_id, "score": 0.9, "text": "gold text"},
            {"rank": 2, "passage_id": "other_1", "evidence_id": "other_1", "score": 0.5, "text": "other text"},
            {"rank": 3, "passage_id": f"{evidence_id}_chunk2", "evidence_id": evidence_id, "score": 0.4, "text": "gold text chunk2"},
        ]
        return retrieved, True, 1.0

    def build_context(self, retrieved, max_tokens=None):
        return "\n".join(f"[Passage {p['rank']}] {p['text']}" for p in retrieved)

    def get_evidence_chunks(self, evidence_id, top_k=None):
        return [{"rank": 1, "passage_id": evidence_id, "evidence_id": evidence_id, "score": 1.0, "text": "oracle text"}]


def test_evidence_ids_used_matches_spec_table(tmp_path):
    """README §9.10: C0->[]; C1->[gold]; C2->deduped retrieval evidence_ids;
    C3 identical to C2 for the same (item, language)."""
    item = _make_item()
    builder = PromptBuilder("configs/prompts")
    cache = GenerationCache(tmp_path / "cache.db")
    runner = GenerationRunner(
        run_id="evidence_test",
        items=[item],
        languages=["bn"],
        conditions=["C0", "C1", "C2", "C3"],
        models=[{"id": "dummy", "adapter": "dummy", "params": {"response": "x"}}],
        prompt_builder=builder,
        cache=cache,
        retriever=FakeRetriever(),
        output_dir=tmp_path,
    )
    generations = runner.generate_all()
    by_condition = {g.condition: g for g in generations}

    assert by_condition["C0"].evidence_ids_used == []
    assert by_condition["C1"].evidence_ids_used == ["ev_gen_0001"]
    assert by_condition["C2"].evidence_ids_used == ["ev_gen_0001", "other_1"]
    assert by_condition["C3"].evidence_ids_used == by_condition["C2"].evidence_ids_used

    # Exactly one RetrievalLog for this (item, language), reused by C2 and C3.
    assert len(runner.retrieval_logs) == 1
    log = runner.retrieval_logs[0]
    assert log.gold_retrieved is True
    assert log.recall_at_k == 1.0
    assert log.index_version == "idx_test"
    assert log.corpus_version == "corpus_test"


def test_cache_hit_skips_second_adapter_call(tmp_path):
    """Resumability: calling generate_all() twice on the same runner must
    hit the cache the second time rather than re-invoking the adapter."""
    item = _make_item()
    builder = PromptBuilder("configs/prompts")
    cache = GenerationCache(tmp_path / "cache.db")
    runner = GenerationRunner(
        run_id="cache_test",
        items=[item],
        languages=["bn"],
        conditions=["C0"],
        models=[{"id": "dummy", "adapter": "dummy", "params": {"response": "x"}}],
        prompt_builder=builder,
        cache=cache,
        output_dir=tmp_path,
    )
    first = runner.generate_all()
    assert runner.generated_count == 1

    second = runner.generate_all()
    assert len(second) == 1
    # generated_count should not have incremented again (cache hit path).
    assert runner.generated_count == 1


def test_prelabel_json_extraction_handles_fences_and_chatter():
    fenced = '```json\n{"a": 1, "b": "x"}\n```'
    assert _extract_json(fenced) == {"a": 1, "b": "x"}

    chatty = 'Sure, here it is: {"a": 1, "b": "x"} — hope that helps!'
    assert _extract_json(chatty) == {"a": 1, "b": "x"}

    plain = '{"a": 1, "b": "x"}'
    assert _extract_json(plain) == {"a": 1, "b": "x"}


def test_annotation_store_roundtrip_and_overlap_disagreement(tmp_path):
    store = AnnotationStore(tmp_path)
    now = datetime.now(timezone.utc).isoformat()

    ann1 = Annotation(
        generation_id="gid1", annotator_id="a1", labeler_type="human",
        correctness="correct", hallucination="no", error_type="none",
        abstention_status="none", timestamp=now, is_overlap=True, verified_by_human=True,
    )
    ann2 = Annotation(
        generation_id="gid1", annotator_id="a2", labeler_type="human",
        correctness="incorrect", hallucination="yes", error_type="H2",
        abstention_status="none", timestamp=now, is_overlap=True, verified_by_human=True,
    )
    store.save_annotation(ann1)
    store.save_annotation(ann2)

    assert store.get_annotation_by_annotator("gid1", "a1")["correctness"] == "correct"
    assert {"gid1"} <= store.annotated_generation_ids()
    disagreements = {d["generation_id"] for d in store.disagreements_in_overlap()}
    assert "gid1" in disagreements
    store.close()

    # Mirror rebuilds correctly from the JSONL file of record on restart.
    store2 = AnnotationStore(tmp_path)
    assert "gid1" in store2.annotated_generation_ids()
    store2.close()


def test_auth_rejects_bad_token_and_unsafe_bind(tmp_path):
    tokens_path = tmp_path / "tokens.json"
    tokens_path.write_text('{"tok123": "annotator_1"}', encoding="utf-8")

    auth_config = {"enabled": True, "provider": "token"}
    assert authenticate("tok123", auth_config, tokens_path) == "annotator_1"

    with pytest.raises(AuthError):
        authenticate("wrong_token", auth_config, tokens_path)

    with pytest.raises(AuthError):
        assert_safe_to_disable_auth("0.0.0.0:8501", {"enabled": False})

    # Localhost bind is fine when auth is (deliberately) disabled.
    assert_safe_to_disable_auth("127.0.0.1:8501", {"enabled": False})
