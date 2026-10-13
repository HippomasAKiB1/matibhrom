import json
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


def test_role_auth_and_adjudication_save(tmp_path):
    from src.annotation.auth import authenticate_with_role
    from src.schema import Adjudication

    tokens_path = tmp_path / "tokens.json"
    tokens_path.write_text(
        json.dumps({
            "tok_ann": "annotator_1",
            "tok_adj": {"annotator_id": "lead_adj", "role": "adjudicator"},
        }),
        encoding="utf-8",
    )

    auth_config = {"enabled": True, "provider": "token"}
    user_id, role = authenticate_with_role("tok_ann", auth_config, tokens_path)
    assert user_id == "annotator_1"
    assert role == "annotator"

    adj_id, adj_role = authenticate_with_role("tok_adj", auth_config, tokens_path)
    assert adj_id == "lead_adj"
    assert adj_role == "adjudicator"

    # Test adjudication record creation and store roundtrip
    store = AnnotationStore(tmp_path)
    adj = Adjudication(
        codebook_version="1.0.0",
        generation_id="gid1",
        adjudicator_id="lead_adj",
        final_correctness="correct",
        final_hallucination="no",
        final_error_type="none",
        rationale="Evidence in passage 1 confirms gold answer.",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    store.save_adjudication(adj)

    # Verify JSONL and SQLite mirror
    assert store.adjudications_path.exists()
    row = store.conn.execute("SELECT adjudicator_id, final_correctness FROM adjudications WHERE generation_id = 'gid1'").fetchone()
    assert row[0] == "lead_adj"
    assert row[1] == "correct"
    store.close()


def test_faiss_index_dimension_and_roundtrip(tmp_path):
    import numpy as np
    from src.rag.index import Index

    dim = 1024
    idx = Index(embedding_dim=dim)
    emb = np.random.randn(5, dim).astype("float32")
    emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)
    passage_ids = [f"p_{i}" for i in range(5)]
    idx.build(emb, passage_ids)

    idx.save(tmp_path, index_version="idx_test_v1")

    # Load in new Index instance
    loaded_idx = Index()
    loaded_idx.load(tmp_path)
    assert loaded_idx.embedding_dim == dim
    assert loaded_idx.metadata.embedding_dim == dim
    assert loaded_idx.metadata.n_passages == 5
    assert loaded_idx.metadata.index_version == "idx_test_v1"

    scores, indices = loaded_idx.search(emb[0], k=2)
    assert indices[0] == 0
    assert pytest.approx(scores[0], rel=1e-4) == 1.0


def test_retriever_chunked_corpus_and_evidence_id_matching(tmp_path):
    import json
    import numpy as np
    from src.rag.index import Index
    from src.rag.retriever import Retriever

    dim = 128
    # Save chunked corpus in index_dir
    index_dir = tmp_path / "index"
    index_dir.mkdir(parents=True)
    chunked = [
        {"passage_id": "ev_001::chunk_0", "text": "chunk 0 text", "evidence_id": "ev_001"},
        {"passage_id": "ev_001::chunk_1", "text": "chunk 1 text", "evidence_id": "ev_001"},
        {"passage_id": "dist_001", "text": "distractor text", "evidence_id": "dist_001"},
    ]
    with open(index_dir / "chunked_corpus.jsonl", "w", encoding="utf-8") as f:
        for c in chunked:
            f.write(json.dumps(c) + "\n")

    # Build and save index
    idx = Index(embedding_dim=dim)
    emb = np.random.randn(3, dim).astype("float32")
    emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)
    idx.build(emb, [c["passage_id"] for c in chunked])
    idx.save(index_dir, index_version="idx_test")

    # Create dummy raw corpus file
    raw_corpus = tmp_path / "corpus.jsonl"
    with open(raw_corpus, "w", encoding="utf-8") as f:
        f.write(json.dumps({"passage_id": "ev_001", "text": "gold full text"}) + "\n")
        f.write(json.dumps({"passage_id": "dist_001", "text": "distractor text"}) + "\n")

    retriever = Retriever(
        corpus_path=raw_corpus,
        index_dir=index_dir,
        top_k=2,
    )

    # Mock embedder to return vector closest to index 1 (chunk 1 of gold)
    class FakeEmbedder:
        def encode_single(self, query):
            return emb[1]

    retriever._embedder = FakeEmbedder()

    results, gold_retrieved, recall_at_k = retriever.retrieve_for_item(
        item_id="item_1",
        question="test query",
        evidence_id="ev_001",
        top_k=2,
    )

    assert gold_retrieved is True
    assert recall_at_k == 1.0
    # Base evidence_id is preserved despite chunk suffix
    assert results[0]["evidence_id"] == "ev_001"
    assert results[0]["passage_id"] == "ev_001::chunk_1"

    # get_evidence_chunks returns oracle gold chunks from raw corpus
    oracle = retriever.get_evidence_chunks("ev_001")
    assert len(oracle) >= 1
    assert oracle[0]["evidence_id"] == "ev_001"
    assert "gold full text" in oracle[0]["text"]

    # build_context truncation test
    ctx = retriever.build_context(results, max_tokens=2)
    assert len(ctx.split()) <= 5  # truncated words/tokens


def test_annotation_scopes():
    from scripts.sample_for_annotation import select_scope_a, select_scope_b, select_scope_c

    sample_gens = [
        {"generation_id": f"g_{i}", "condition": f"C{i%4}", "model_id": "m1", "language": "bn", "domain": "general"}
        for i in range(20)
    ]

    # Scope A
    scope_a = select_scope_a(sample_gens, stratified_max=10)
    assert len(scope_a) <= 10 and len(scope_a) > 0

    # Scope B: drops C0
    scope_b = select_scope_b(sample_gens)
    assert all(g["condition"] != "C0" for g in scope_b)
    assert len(scope_b) == 15  # 20 - 5 C0 items

    # Scope C: 100% of generations
    scope_c = select_scope_c(sample_gens)
    assert len(scope_c) == len(sample_gens)


def test_compute_iaa_and_pilot_gate():
    from scripts.compute_iaa import compute_pairwise_iaa

    # Case 1: High agreement (both raters agree on almost everything)
    annotations_high = [
        # gen_1: both say correct, no hallucination
        {"generation_id": "g1", "annotator_id": "r1", "hallucination": "no", "correctness": "correct", "error_type": "none", "abstention_status": "none"},
        {"generation_id": "g1", "annotator_id": "r2", "hallucination": "no", "correctness": "correct", "error_type": "none", "abstention_status": "none"},
        # gen_2: both say yes hallucination, incorrect
        {"generation_id": "g2", "annotator_id": "r1", "hallucination": "yes", "correctness": "incorrect", "error_type": "H1", "abstention_status": "none"},
        {"generation_id": "g2", "annotator_id": "r2", "hallucination": "yes", "correctness": "incorrect", "error_type": "H1", "abstention_status": "none"},
        # gen_3: both say no hallucination, correct
        {"generation_id": "g3", "annotator_id": "r1", "hallucination": "no", "correctness": "correct", "error_type": "none", "abstention_status": "none"},
        {"generation_id": "g3", "annotator_id": "r2", "hallucination": "no", "correctness": "correct", "error_type": "none", "abstention_status": "none"},
    ]
    res_high = compute_pairwise_iaa(annotations_high)
    assert res_high["num_overlap_pairs"] == 3
    assert res_high["metrics"]["hallucination"]["cohens_kappa"] == 1.0
    assert res_high["metrics"]["correctness"]["cohens_kappa"] == 1.0

    # Case 2: Poor agreement (conflicting ratings)
    annotations_low = [
        {"generation_id": "g1", "annotator_id": "r1", "hallucination": "yes", "correctness": "incorrect"},
        {"generation_id": "g1", "annotator_id": "r2", "hallucination": "no", "correctness": "correct"},
        {"generation_id": "g2", "annotator_id": "r1", "hallucination": "no", "correctness": "correct"},
        {"generation_id": "g2", "annotator_id": "r2", "hallucination": "yes", "correctness": "incorrect"},
    ]
    res_low = compute_pairwise_iaa(annotations_low)
    assert res_low["num_overlap_pairs"] == 2
    assert res_low["metrics"]["hallucination"]["cohens_kappa"] < 0.70


