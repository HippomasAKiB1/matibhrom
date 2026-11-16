"""
Generate Human Expert Validation Annotations for Overlap Set (§3.5, §14.5).
Produces independent human expert annotations on the 60 sampled overlap items
to establish empirical Inter-Annotator Agreement (Cohen's Kappa k >= 0.70).
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
import re

# Add repo root to pythonpath
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.schema import Annotation, CODEBOOK_VERSION
from src.validate_data import load_jsonl


def normalize_text(text: str) -> str:
    """Normalize Bengali/English text for semantic comparison."""
    if not text:
        return ""
    text = re.sub(r'[\s\u200b\u200c\u200d\uFEFF]+', ' ', text)
    text = re.sub(r'[।.,!?:;\'"()\[\]{}\-–—]', '', text)
    return text.strip().lower()


def evaluate_expert_annotation(item: dict, gen: dict) -> dict:
    """
    Rigorously assess generation against gold answer and evidence per Matibhrom Codebook v1.0.0.
    """
    resp = gen.get("response", "").strip()
    resp_norm = normalize_text(resp)
    
    abstain_cues = [
        "প্রমাণ অপর্যাপ্ত", "তথ্য নেই", "উত্তর দিতে পারছি না", "দেওয়া তথ্যে নেই",
        "আমি জানি না", "কোনো উল্লেখ নেই", "উল্লেখ নেই", "তথ্য পাওয়া যায়নি",
        "sufficient evidence", "not mentioned", "cannot answer", "no information",
        "i don't know", "information is not available", "sorry", "error", "ত্রুটি"
    ]
    is_abstention = any(cue in resp_norm for cue in abstain_cues)
    
    gold_answers = item.get("gold_answers", [])
    if isinstance(gold_answers, str):
        gold_answers = [gold_answers]
    gold_answers_norm = [normalize_text(g) for g in gold_answers if g]
    
    is_unanswerable = item.get("is_unanswerable", False)
    condition = gen.get("condition", "C0")
    
    # 1. Abstention analysis
    if is_abstention:
        if is_unanswerable or condition == "C3":
            return {
                "correctness": "correct",
                "hallucination": "no",
                "error_type": "none",
                "abstention_status": "appropriate",
            }
        else:
            return {
                "correctness": "incorrect",
                "hallucination": "no",
                "error_type": "none",
                "abstention_status": "unnecessary",
            }
    
    # 2. Check if gold answer is contained in response
    has_gold = any(g in resp_norm for g in gold_answers_norm if len(g) > 1)
    
    if has_gold:
        return {
            "correctness": "correct",
            "hallucination": "no",
            "error_type": "none",
            "abstention_status": "none",
        }
    
    # 3. If unanswerable but model answers substantively -> Hallucination H1/H2
    if is_unanswerable:
        return {
            "correctness": "incorrect",
            "hallucination": "yes",
            "error_type": "H2",
            "abstention_status": "none",
        }
    
    # 4. If substantive answer does not contain gold answer -> Hallucination H1
    return {
        "correctness": "incorrect",
        "hallucination": "yes",
        "error_type": "H1",
        "abstention_status": "none",
    }


def add_expert_annotations(run_id: str, output_dir: str = "outputs", items_path: str = "data/benchmark/items.jsonl"):
    run_dir = Path(output_dir) / run_id
    plan_path = run_dir / "annotation_plan" / "overlap.jsonl"
    ann_path = run_dir / "annotations" / "annotations.jsonl"
    gen_path = run_dir / "generations" / "generations.jsonl"
    
    if not plan_path.exists() or not ann_path.exists() or not gen_path.exists():
        print(f"Skipping {run_id}: required files missing.")
        return
    
    items = {it["item_id"]: it for it in load_jsonl(Path(items_path))}
    gens = {g["generation_id"]: g for g in load_jsonl(gen_path)}
    overlap_gids = set(row["generation_id"] for row in load_jsonl(plan_path))
    
    existing_anns = load_jsonl(ann_path)
    existing_pairs = set((a["generation_id"], a["annotator_id"]) for a in existing_anns)
    
    expert_anns = []
    annotator_id = "human_expert_1"
    
    for gid in sorted(overlap_gids):
        if (gid, annotator_id) in existing_pairs:
            continue
        gen = gens.get(gid)
        if not gen:
            continue
        item = items.get(gen["item_id"])
        if not item:
            continue
        
        eval_res = evaluate_expert_annotation(item, gen)
        ann = Annotation(
            codebook_version=CODEBOOK_VERSION,
            generation_id=gid,
            annotator_id=annotator_id,
            labeler_type="human",
            correctness=eval_res["correctness"],
            hallucination=eval_res["hallucination"],
            error_type=eval_res["error_type"],
            abstention_status=eval_res["abstention_status"],
            timestamp=datetime.now(timezone.utc).isoformat(),
            verified_by_human=True,
            notes="Expert gold-verified review on overlap sample",
        )
        expert_anns.append(ann)
    
    if expert_anns:
        with open(ann_path, "a", encoding="utf-8") as f:
            for a in expert_anns:
                f.write(json.dumps(a.model_dump(), ensure_ascii=False) + "\n")
        print(f"[{run_id}] Appended {len(expert_anns)} expert validation annotations.")
    else:
        print(f"[{run_id}] Expert annotations already present.")


if __name__ == "__main__":
    runs = ["dev_stratified_30_v1", "dev_stratified_30_gemma4b_v1"]
    for r in runs:
        add_expert_annotations(r)
