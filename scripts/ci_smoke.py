"""
CI smoke test for Matibhrom benchmark pipeline.
Runs strictly offline without network access using dummy data,
dummy model adapter, and local retrieval index.
"""

import os
import sys
import shutil
import tempfile
from pathlib import Path

# Enforce offline mode
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# Repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.validate_data import validate_artifact
from src.schema import Item, Evidence, CorpusPassage, Generation, Annotation
from src.prompts.builder import PromptBuilder
from src.runner.cache import GenerationCache
from src.runner.generate import GenerationRunner
from scripts.sample_for_annotation import select_scope_a, stratified_overlap, write_plan
from scripts.compute_iaa import compute_pairwise_iaa
from scripts.export_tables import (
    join_generations_and_annotations,
    compute_bootstrap_cis,
    compute_paired_comparisons,
    compute_retrieval_diagnostics,
    write_latex_table,
    write_retrieval_report,
    append_stats_to_summary,
    build_token_counts_by_model_language,
    write_plots,
)
from src.eval.metrics import compute_metrics_by_group, generate_metrics_csv, generate_summary_markdown
from src.eval.report import generate_tokenization_report


from src.io_atomic import stop_all_writers


class DummyRetriever:
    top_k = 2
    index_version = "smoke_v1"
    corpus_version = "smoke_v1"

    def retrieve_for_item(self, item_id, question, evidence_id, top_k=2):
        retrieved = [
            {"rank": 1, "passage_id": evidence_id, "evidence_id": evidence_id, "score": 0.95, "text": "নমুনা প্রমাণ বাক্য।"},
            {"rank": 2, "passage_id": "dist_01", "evidence_id": "dist_01", "score": 0.60, "text": "অন্যান্য তথ্য।"},
        ]
        return retrieved, True, 1.0

    def build_context(self, retrieved, max_tokens=None):
        return "\n".join(f"[Passage {p['rank']}] {p['text']}" for p in retrieved)

    def get_evidence_chunks(self, evidence_id, top_k=None):
        return [{"rank": 1, "passage_id": evidence_id, "evidence_id": evidence_id, "score": 1.0, "text": "ওরাকল প্রমাণ।"}]


def run_smoke():
    print("=" * 60)
    print("RUNNING MATIBHROM CI SMOKE SUITE (OFFLINE / ZERO-NETWORK)")
    print("=" * 60)

    # 1. Validate dataset
    print("[1/6] Validating dummy dataset schemas and invariants...")
    data_dir = REPO_ROOT / "data" / "dummy"
    errors = validate_artifact(
        data_dir / "items.jsonl",
        data_dir / "evidence.jsonl",
        data_dir / "corpus.jsonl",
        min_corpus_passages=1,
    )
    assert not errors, f"Dataset validation errors: {errors}"
    print("  -> Dataset validation OK.")

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        tmp_path = Path(tmpdir)
        run_id = "smoke_run"
        output_dir = tmp_path / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)

        # 2. Generation loop with dummy adapter
        print("[2/6] Running end-to-end generation runner (C0..C3, bn/banglish)...")
        prompt_builder = PromptBuilder(REPO_ROOT / "configs" / "prompts")
        cache = GenerationCache(tmp_path / "cache.db")
        item = Item.model_validate({
            "schema_version": "1.0.0",
            "item_id": "smoke_item_01",
            "domain": "general",
            "question_bn": "বাংলাদেশের রাজধানী কী?",
            "question_banglish": "Bangladesh er rajdhani ki?",
            "gold_answer": "ঢাকা",
            "evidence_id": "smoke_ev_01",
            "answer_type": "entity",
            "risk_tag": "normal",
            "split": "dev",
            "group_key": None,
        })
        model_config = {
            "id": "dummy_model",
            "adapter": "dummy",
            "params": {"response": "ঢাকা বাংলাদেশের রাজধানী।"},
        }
        retriever = DummyRetriever()
        runner = GenerationRunner(
            run_id=run_id,
            items=[item],
            languages=["bn", "banglish"],
            conditions=["C0", "C1", "C2", "C3"],
            models=[model_config],
            prompt_builder=prompt_builder,
            cache=cache,
            retriever=retriever,
            output_dir=output_dir,
            workers=2,
        )
        generations = runner.generate_all()
        assert len(generations) == 8, f"Expected 8 generations, got {len(generations)}"
        assert runner.generations_path.exists(), "generations.jsonl missing"
        print(f"  -> Generated {len(generations)} records successfully.")

        # 3. Annotation sampling
        print("[3/6] Running annotation plan sampling...")
        gen_dicts = [g.model_dump() for g in generations]
        primary = select_scope_a(gen_dicts, seed=42)
        overlap = stratified_overlap(primary, fraction=0.5, seed=42)
        overlap_ids = {g["generation_id"] for g in overlap}
        assert len(primary) == 8
        print(f"  -> Sampled {len(primary)} primary, {len(overlap)} overlap.")

        # 4. Synthesize annotations & test IAA
        print("[4/6] Computing Inter-Annotator Agreement (Cohen's kappa)...")
        annotations = []
        for g in generations:
            ann1 = {
                "schema_version": "1.0.0",
                "codebook_version": "1.0.0",
                "generation_id": g.generation_id,
                "annotator_id": "r1",
                "labeler_type": "human",
                "correctness": "correct",
                "hallucination": "no",
                "error_type": "none",
                "abstention_status": "none",
                "is_overlap": g.generation_id in overlap_ids,
                "verified_by_human": True,
            }
            annotations.append(ann1)
            if g.generation_id in overlap_ids:
                ann2 = dict(ann1, annotator_id="r2")
                annotations.append(ann2)

        iaa_results = compute_pairwise_iaa(annotations)
        assert iaa_results["num_overlap_pairs"] == len(overlap)
        assert iaa_results["metrics"]["hallucination"]["cohens_kappa"] == 1.0
        print(f"  -> Cohen's kappa IAA OK (pairs={iaa_results['num_overlap_pairs']}, kappa=1.00).")

        # 5. Export tables, stats, diagnostics
        print("[5/6] Exporting metrics, tables, bootstrap CIs, and retrieval diagnostics...")
        reports_dir = output_dir / run_id / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        item_domain = {item.item_id: item.domain}
        joined = join_generations_and_annotations(gen_dicts, annotations, item_domain)
        retrieval_logs = [l.model_dump() for l in runner.retrieval_logs]

        metrics_by_group = compute_metrics_by_group(joined, "condition", retrieval_logs)
        cis = compute_bootstrap_cis(joined, "condition")
        paired = compute_paired_comparisons(joined)
        diag = compute_retrieval_diagnostics(retrieval_logs, item_domain)

        generate_metrics_csv(metrics_by_group, reports_dir / "metrics.csv")
        generate_summary_markdown(metrics_by_group, "Smoke findings.", reports_dir / "summary.md")
        write_latex_table(metrics_by_group, cis, reports_dir / "tables" / "primary_metrics.tex")
        write_retrieval_report(diag, reports_dir / "retrieval_diagnostics.md")
        append_stats_to_summary(reports_dir / "summary.md", cis, paired, diag)
        token_counts = build_token_counts_by_model_language(gen_dicts)
        generate_tokenization_report(token_counts, reports_dir / "tokenization_report.md")
        plotted = write_plots(metrics_by_group, reports_dir / "plots")

        # 6. Verify artifacts
        print("[6/6] Verifying exported artifact integrity...")
        assert (reports_dir / "metrics.csv").exists()
        assert (reports_dir / "summary.md").exists()
        assert (reports_dir / "tables" / "primary_metrics.tex").exists()
        assert (reports_dir / "retrieval_diagnostics.md").exists()
        assert (reports_dir / "tokenization_report.md").exists()
        assert len(plotted) > 0
        print(f"  -> Artifacts generated: metrics.csv, summary.md, primary_metrics.tex, retrieval_diagnostics.md, tokenization_report.md, {len(plotted)} plots.")

        # Cleanup handles
        stop_all_writers()
        cache.close()

    print("=" * 60)
    print("[CI SMOKE PASSED] All pipeline components verified cleanly offline.")
    print("=" * 60)


if __name__ == "__main__":
    run_smoke()
