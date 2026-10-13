import csv
from pathlib import Path
import pytest
from src.eval.metrics import generate_metrics_csv
from src.schema import Generation
from src.schema_version import SCHEMA_VERSION
from scripts.migrate_schema import migrate_record, MIGRATIONS


def test_generate_metrics_csv_empty_input(tmp_path: Path):
    out_csv = tmp_path / "empty_metrics.csv"
    # Should not raise StopIteration on empty input
    generate_metrics_csv({}, out_csv)
    assert out_csv.exists()
    content = out_csv.read_text(encoding="utf-8").strip()
    assert content == "group"


def test_generate_metrics_csv_normal_input(tmp_path: Path):
    out_csv = tmp_path / "normal_metrics.csv"
    data = {
        "C0": {"hallucination_rate": 0.25, "coverage": 1.0},
        "C1": {"hallucination_rate": 0.10, "coverage": 0.9},
    }
    generate_metrics_csv(data, out_csv)
    assert out_csv.exists()
    rows = list(csv.reader(out_csv.read_text(encoding="utf-8").splitlines()))
    assert rows[0] == ["group", "hallucination_rate", "coverage"]
    assert rows[1] == ["C0", "0.25", "1.0"]
    assert rows[2] == ["C1", "0.1", "0.9"]


def test_generation_truncated_input_schema():
    # Record without truncated_input should validate and default to False
    base_data = {
        "schema_version": SCHEMA_VERSION,
        "run_id": "test_run",
        "generation_id": "gen_001",
        "item_id": "item_001",
        "language": "bn",
        "condition": "C0",
        "model_id": "test_model",
        "model_version": "v1",
        "prompt": "Test prompt",
        "prompt_hash": "abc",
        "prompt_tokens": 10,
        "response": "Test response",
        "response_tokens": 5,
    }
    gen = Generation.model_validate(base_data)
    assert gen.truncated_input is False

    # Record with truncated_input=True
    data_with_trunc = dict(base_data, truncated_input=True)
    gen2 = Generation.model_validate(data_with_trunc)
    assert gen2.truncated_input is True


def test_migrate_schema_harness():
    # Test migration harness logic
    MIGRATIONS["generation"]["0.9.0"] = lambda rec: dict(rec, schema_version="1.0.0", truncated_input=False)
    try:
        old_rec = {
            "schema_version": "0.9.0",
            "run_id": "run_0",
            "generation_id": "gen_old",
            "item_id": "item_1",
            "language": "bn",
            "condition": "C0",
            "model_id": "m1",
            "model_version": "v1",
            "prompt": "p",
            "prompt_hash": "h",
            "prompt_tokens": 1,
            "response": "r",
            "response_tokens": 1,
        }
        migrated = migrate_record(old_rec, "generation", target_version="1.0.0")
        assert migrated["schema_version"] == "1.0.0"
        assert migrated["truncated_input"] is False
    finally:
        MIGRATIONS["generation"].pop("0.9.0", None)


def test_export_tables_pipeline_with_stats_and_retrieval_diag(tmp_path: Path):
    from scripts.export_tables import (
        compute_bootstrap_cis,
        compute_paired_comparisons,
        compute_retrieval_diagnostics,
        write_latex_table,
    )

    joined = [
        {"item_id": "i1", "model_id": "m1", "condition": "C0", "language": "bn", "hallucination": "yes", "correctness": "incorrect"},
        {"item_id": "i1", "model_id": "m1", "condition": "C0", "language": "banglish", "hallucination": "yes", "correctness": "incorrect"},
        {"item_id": "i1", "model_id": "m1", "condition": "C1", "language": "bn", "hallucination": "no", "correctness": "correct"},
        {"item_id": "i1", "model_id": "m1", "condition": "C1", "language": "banglish", "hallucination": "no", "correctness": "correct"},
        {"item_id": "i2", "model_id": "m1", "condition": "C0", "language": "bn", "hallucination": "yes", "correctness": "incorrect"},
        {"item_id": "i2", "model_id": "m1", "condition": "C1", "language": "bn", "hallucination": "no", "correctness": "correct"},
    ]

    # 1. Bootstrap CIs
    cis = compute_bootstrap_cis(joined, group_by="condition")
    assert "C0" in cis and "C1" in cis
    assert "hallucination" in cis["C0"]
    assert cis["C0"]["hallucination"]["mean"] == 1.0
    assert cis["C1"]["hallucination"]["mean"] == 0.0

    # 2. Paired McNemar tests
    paired = compute_paired_comparisons(joined)
    assert "bn_vs_banglish" in paired
    assert "c0_vs_c1_hallucination" in paired
    assert "statistic" in paired["c0_vs_c1_hallucination"]

    # 3. Retrieval diagnostics
    logs = [
        {
            "item_id": "i1",
            "language": "bn",
            "gold_evidence_id": "ev1",
            "gold_retrieved": True,
            "retrieved": [{"rank": 1, "evidence_id": "ev1"}],
        },
        {
            "item_id": "i2",
            "language": "banglish",
            "gold_evidence_id": "ev2",
            "gold_retrieved": False,
            "retrieved": [{"rank": 1, "evidence_id": "other"}],
        },
    ]
    diag = compute_retrieval_diagnostics(logs, {"i1": "general", "i2": "medical"})
    assert diag["overall"]["queries"] == 2
    assert diag["overall"]["recall_at_k"] == 0.5
    assert diag["overall"]["rank_1_rate"] == 0.5
    assert diag["by_language"]["bn"]["recall_at_k"] == 1.0
    assert diag["by_language"]["banglish"]["recall_at_k"] == 0.0
    assert diag["by_domain"]["medical"]["recall_at_k"] == 0.0

    # 4. LaTeX table with 95% CIs
    tex_path = tmp_path / "table.tex"
    metrics_by_group = {
        "C0": {"hallucination_rate": 1.0, "coverage": 1.0, "selective_accuracy": 0.0, "abstention_rate": 0.0},
        "C1": {"hallucination_rate": 0.0, "coverage": 1.0, "selective_accuracy": 1.0, "abstention_rate": 0.0},
    }
    write_latex_table(metrics_by_group, cis, tex_path)
    assert tex_path.exists()
    tex_content = tex_path.read_text(encoding="utf-8")
    assert r"\begin{tabular}" in tex_content
    assert "C0 & 1.000 [1.00, 1.00]" in tex_content

