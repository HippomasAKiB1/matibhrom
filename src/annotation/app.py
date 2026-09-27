"""
Streamlit annotation UI for Matibhrom (README §14.3).

Run with:
    streamlit run src/annotation/app.py -- --run-id main_v1

Show: question (in the item's language), gold answer, C1 evidence
(chunk-matched, §8.10), model response.
Hide: model identity, condition, domain (unless needed during adjudication).
Fields: correctness, hallucination, error type, abstention status, notes.
Behavior: immediate save to JSONL + SQLite mirror; randomized order; progress
counter; jump-to-generation; keyboard shortcuts; LLM pre-label shown
alongside response (annotator may accept or override).
"""

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import yaml

from src.annotation.auth import AuthError, authenticate
from src.annotation.store import AnnotationStore
from src.schema import Annotation
from src.schema_version import CODEBOOK_VERSION
from src.validate_data import load_jsonl

CORRECTNESS_OPTIONS = ["correct", "partially_correct", "incorrect"]
HALLUCINATION_OPTIONS = ["no", "yes"]
ERROR_TYPE_OPTIONS = ["none", "H1", "H2", "H3", "H4", "H5", "A", "R"]
ABSTENTION_OPTIONS = ["none", "appropriate", "unnecessary"]

ERROR_TYPE_LABELS = {
    "none": "none",
    "H1": "H1 — Contradiction",
    "H2": "H2 — Unsupported addition",
    "H3": "H3 — Fabricated entity/citation",
    "H4": "H4 — Numeric/temporal error",
    "H5": "H5 — Inference error",
    "A": "A — Appropriate abstention",
    "R": "R — Unnecessary refusal",
}


def _parse_cli_args() -> argparse.Namespace:
    # Streamlit passes everything after `--` in sys.argv unmodified.
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--items", default="data/dummy/items.jsonl")
    parser.add_argument("--evidence", default="data/dummy/evidence.jsonl")
    parser.add_argument("--config", default="configs/annotation.yaml")
    parser.add_argument("--tokens", default="configs/annotation_tokens.json")
    args, _ = parser.parse_known_args(sys.argv[1:])
    return args


@st.cache_resource
def load_run_data(run_id: str, output_dir: str, items_path: str, evidence_path: str):
    run_dir = Path(output_dir) / run_id
    generations = load_jsonl(run_dir / "generations" / "generations.jsonl")
    items_by_id = {i["item_id"]: i for i in load_jsonl(Path(items_path))}

    evidence_by_id = {}
    if Path(evidence_path).exists():
        evidence_by_id = {e["evidence_id"]: e for e in load_jsonl(Path(evidence_path))}

    plan_path = run_dir / "annotation_plan" / "primary.jsonl"
    if plan_path.exists():
        allowed_ids = {r["generation_id"] for r in load_jsonl(plan_path)}
        generations = [g for g in generations if g["generation_id"] in allowed_ids]

    overlap_path = run_dir / "annotation_plan" / "overlap.jsonl"
    overlap_ids = {r["generation_id"] for r in load_jsonl(overlap_path)} if overlap_path.exists() else set()

    verify_path = run_dir / "annotation_plan" / "verify_required.jsonl"
    verify_required_ids = (
        {r["generation_id"] for r in load_jsonl(verify_path)} if verify_path.exists() else set()
    )

    return generations, items_by_id, evidence_by_id, overlap_ids, verify_required_ids


def get_prelabel(store: AnnotationStore, generation_id: str) -> dict | None:
    """The LLM pre-label for this generation, if one exists and hasn't
    already been converted to a human label."""
    for row in store.get_annotations_for_generation(generation_id):
        if row["labeler_type"] == "llm":
            return row
    return None


def render_annotation_form(
    store: AnnotationStore,
    generation: dict,
    item: dict,
    evidence_by_id: dict,
    annotator_id: str,
    is_overlap: bool,
    codebook_version: str,
) -> None:
    prelabel = get_prelabel(store, generation["generation_id"])
    existing = store.get_annotation_by_annotator(generation["generation_id"], annotator_id)

    question = item["question_bn"] if generation["language"] == "bn" else item["question_banglish"]

    st.subheader("প্রশ্ন (Question)")
    st.write(question)

    st.subheader("সঠিক উত্তর (Gold answer)")
    st.write(item["gold_answer"])

    # C1 chunk-matched evidence (§8.10): the item's gold evidence_id, joined
    # against evidence.jsonl for the full text.
    evidence = evidence_by_id.get(item["evidence_id"])
    if evidence:
        st.subheader("প্রমাণ (Evidence)")
        st.write(evidence["text"])

    st.subheader("মডেলের উত্তর (Response)")
    st.write(generation["response"])

    if prelabel:
        with st.expander("LLM pre-label (accept or override below)", expanded=True):
            st.json({
                "correctness": prelabel["correctness"],
                "hallucination": prelabel["hallucination"],
                "error_type": prelabel["error_type"],
                "abstention_status": prelabel["abstention_status"],
            })

    # Pre-fill defaults: existing human label > LLM pre-label > blank first option.
    source = existing or prelabel or {}
    default_correctness = source.get("correctness") or CORRECTNESS_OPTIONS[0]
    default_hallucination = source.get("hallucination") or HALLUCINATION_OPTIONS[0]
    default_error_type = source.get("error_type") or "none"
    default_abstention = source.get("abstention_status") or "none"
    default_notes = source.get("notes", "") if existing else ""

    with st.form(key=f"form_{generation['generation_id']}"):
        correctness = st.radio(
            "Correctness", CORRECTNESS_OPTIONS,
            index=CORRECTNESS_OPTIONS.index(default_correctness), horizontal=True,
        )
        hallucination = st.radio(
            "Hallucination", HALLUCINATION_OPTIONS,
            index=HALLUCINATION_OPTIONS.index(default_hallucination), horizontal=True,
        )
        error_type = st.selectbox(
            "Error type", ERROR_TYPE_OPTIONS,
            index=ERROR_TYPE_OPTIONS.index(default_error_type),
            format_func=lambda k: ERROR_TYPE_LABELS[k],
        )
        abstention_status = st.radio(
            "Abstention status", ABSTENTION_OPTIONS,
            index=ABSTENTION_OPTIONS.index(default_abstention), horizontal=True,
        )
        tier2_candidate = st.checkbox(
            "Flag as tier-2 abstention candidate",
            value=bool(source.get("tier2_abstention_candidate", False)),
        )
        notes = st.text_area("Notes", value=default_notes)

        submitted = st.form_submit_button("Save")

    # Keyboard shortcut: Enter anywhere on the page clicks the visible Save
    # button (the browser's native Enter-submits-form behavior doesn't fire
    # reliably across Streamlit's radio/selectbox widgets, so this is bound
    # explicitly). §14.3 "keyboard shortcuts". st.html (not iframed) is used
    # rather than the deprecated st.components.v1.html so the script can see
    # the real page DOM directly instead of reaching through a parent frame.
    st.html(
        """
        <script>
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                const buttons = document.querySelectorAll('button[kind="formSubmit"]');
                if (buttons.length > 0) {
                    buttons[buttons.length - 1].click();
                    e.preventDefault();
                }
            }
        });
        </script>
        """,
        unsafe_allow_javascript=True,
    )

    if submitted:
        was_llm_prelabel_accepted_or_overridden = prelabel is not None
        annotation = Annotation(
            codebook_version=codebook_version,
            generation_id=generation["generation_id"],
            annotator_id=annotator_id,
            labeler_type="human",
            correctness=correctness,
            hallucination=hallucination,
            error_type=error_type,
            abstention_status=abstention_status,
            tier2_abstention_candidate=tier2_candidate,
            notes=notes,
            timestamp=datetime.now(timezone.utc).isoformat(),
            is_overlap=is_overlap,
            # A human always verifies their own submitted label; the
            # LLM's own unverified pre-label record (labeler_type="llm")
            # is left untouched in the JSONL for the §14.6 IAA appendix.
            verified_by_human=True,
        )
        store.save_annotation(annotation)
        st.success("Saved.")
        st.session_state["advance"] = True
        st.rerun()


def main() -> None:
    args = _parse_cli_args()

    with open(args.config, encoding="utf-8") as f:
        ann_config = yaml.safe_load(f)

    st.set_page_config(page_title="Matibhrom Annotation", layout="wide")

    if "annotator_id" not in st.session_state:
        st.title("Matibhrom Annotation — Sign in")
        token = st.text_input("Annotator token", type="password")
        if st.button("Sign in") and token:
            try:
                annotator_id = authenticate(token, ann_config.get("auth", {"enabled": True}), args.tokens)
                st.session_state["annotator_id"] = annotator_id
                st.rerun()
            except AuthError as e:
                st.error(str(e))
        st.stop()

    annotator_id = st.session_state["annotator_id"]

    generations, items_by_id, evidence_by_id, overlap_ids, verify_required_ids = load_run_data(
        args.run_id, args.output_dir, args.items, args.evidence
    )

    run_dir = Path(args.output_dir) / args.run_id
    store = AnnotationStore(run_dir)

    if "order" not in st.session_state:
        order = list(range(len(generations)))
        if ann_config.get("randomize_order", True):
            random.Random(hash(annotator_id) % (2**31)).shuffle(order)
        st.session_state["order"] = order
        st.session_state["pos"] = 0

    order = st.session_state["order"]
    already_done = store.annotated_generation_ids(annotator_id)

    # Advance past anything this annotator already labeled, on first load.
    if st.session_state.get("advance"):
        st.session_state["pos"] = min(st.session_state["pos"] + 1, len(order) - 1)
        st.session_state["advance"] = False

    st.sidebar.write(f"Signed in as **{annotator_id}**")
    n_done = sum(1 for i in order if generations[i]["generation_id"] in already_done)
    st.sidebar.progress(n_done / max(1, len(order)))
    st.sidebar.write(f"{n_done} / {len(order)} annotated")

    jump_to = st.sidebar.text_input("Jump to generation_id")
    if jump_to:
        matches = [i for i, idx in enumerate(order) if generations[idx]["generation_id"] == jump_to]
        if matches:
            st.session_state["pos"] = matches[0]
        else:
            st.sidebar.warning("generation_id not found in this annotator's set.")

    pos = st.session_state["pos"]
    pos = max(0, min(pos, len(order) - 1))
    st.session_state["pos"] = pos

    col_prev, col_next = st.sidebar.columns(2)
    if col_prev.button("← Previous") and pos > 0:
        st.session_state["pos"] = pos - 1
        st.rerun()
    if col_next.button("Next →") and pos < len(order) - 1:
        st.session_state["pos"] = pos + 1
        st.rerun()

    generation = generations[order[pos]]
    item = items_by_id.get(generation["item_id"])
    if item is None:
        st.error(f"Item {generation['item_id']} not found in {args.items}")
        return

    is_overlap = generation["generation_id"] in overlap_ids
    if generation["generation_id"] in verify_required_ids:
        st.sidebar.warning("This item requires mandatory verification (§14.6).")
    if is_overlap:
        st.sidebar.info("This item is in the overlap sample (second annotator).")

    st.caption(f"generation_id: {generation['generation_id']} — {pos + 1} / {len(order)}")
    # Hidden per §14.3: model identity, condition, domain — not rendered
    # above. They're only surfaced in st.sidebar under an explicit toggle so
    # adjudicators (who legitimately need them) can opt in.
    if st.sidebar.checkbox("Show model/condition/domain (adjudication only)"):
        st.sidebar.write(f"model_id: {generation['model_id']}")
        st.sidebar.write(f"condition: {generation['condition']}")
        st.sidebar.write(f"domain: {item.get('domain')}")

    render_annotation_form(store, generation, item, evidence_by_id, annotator_id, is_overlap, CODEBOOK_VERSION)


if __name__ == "__main__":
    main()
