"""
Generate synthetic stress test dataset for Matibhrom.
Generates:
  - 100 synthetic items (20 dev, 80 test, balanced across domains)
  - 100 gold evidence passages
  - 1,000 synthetic distractor corpus passages (1,100 total corpus passages)

Labeled clearly as synthetic and kept in data/synthetic_stress/.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.schema_version import SCHEMA_VERSION


DOMAINS = ["general", "medical", "legal"]
ANSWER_TYPES = ["entity", "numeric", "short explanation", "citation"]

BN_TEMPLATES = {
    "general": [
        "বাংলাদেশের {place} এর প্রধান নদী কোনটি?",
        "ঐতিহাসিক {entity} কোন সালে নির্মিত হয়েছিল?",
        "{event} এর বার্ষিক গড় বৃষ্টিপাত কত মিলিমিটার?",
    ],
    "medical": [
        "রোগী {symptom} এ আক্রান্ত হলে প্রাথমিক চিকিৎসা কী?",
        "{medicine} এর সাধারণ পার্শ্বপ্রতিক্রিয়া কোনটি?",
        "রক্তে {marker} এর স্বাভাবিক মাত্রা কত?",
    ],
    "legal": [
        "বাংলাদেশ শ্রম আইনের {section} ধারা অনুযায়ী ক্ষতিপূরণের পরিমাণ কত?",
        "সম্পত্তি হস্তান্তর আইনের {section} ধারায় কী বিধান রয়েছে?",
        "{court} এর আপিল দায়ের করার সময়সীমা কত দিন?",
    ],
}

BANGLISH_TEMPLATES = {
    "general": [
        "Bangladesh er {place} er prodhan nodi konti?",
        "Oitihasik {entity} kon shale nirmito hoyechilo?",
        "{event} er barshik gor brishti koto milimitar?",
    ],
    "medical": [
        "Rogi {symptom} e akranto hole prathomik chikitsa ki?",
        "{medicine} er shadharon parshoprotikriya konti?",
        "Rokte {marker} er swabhabik matra koto?",
    ],
    "legal": [
        "Bangladesh shrom aainer {section} dhara onujayi khotipuron koto?",
        "Shompotti hostantor aainer {section} dharay ki bidhan royeche?",
        "{court} er appeal dayer korar shomoyshima koto din?",
    ],
}


def generate_stress_data(output_dir: Path, n_items: int = 100, n_distractors: int = 1000):
    output_dir.mkdir(parents=True, exist_ok=True)
    items_path = output_dir / "items_synthetic.jsonl"
    evidence_path = output_dir / "evidence_synthetic.jsonl"
    corpus_path = output_dir / "corpus_synthetic.jsonl"

    items = []
    evidences = []
    corpus_passages = []

    # 1. Generate Items and Gold Evidence
    for i in range(1, n_items + 1):
        item_id = f"syn_{i:04d}"
        ev_id = f"ev_syn_{i:04d}"
        domain = DOMAINS[(i - 1) % len(DOMAINS)]
        answer_type = ANSWER_TYPES[(i - 1) % len(ANSWER_TYPES)]
        risk_tag = "high-stakes" if domain in ("medical", "legal") else "normal"

        # Split: 20% dev (items 1..20), 80% test (items 21..100)
        split = "dev" if i <= int(n_items * 0.20) else "test"
        group_key = f"grp_{split}_{((i - 1) // 5):02d}"

        bn_q = BN_TEMPLATES[domain][(i - 1) % len(BN_TEMPLATES[domain])].format(
            place=f"জেলা_{i}", entity=f"স্মৃতিস্তম্ভ_{i}", event=f"অঞ্চল_{i}",
            symptom=f"লক্ষণ_{i}", medicine=f"ওষুধ_{i}", marker=f"উপাদান_{i}",
            section=f"{i}ক", court=f"আদালত_{i}"
        )
        banglish_q = BANGLISH_TEMPLATES[domain][(i - 1) % len(BANGLISH_TEMPLATES[domain])].format(
            place=f"jela_{i}", entity=f"sriti_{i}", event=f"onchol_{i}",
            symptom=f"lokkhon_{i}", medicine=f"oshudh_{i}", marker=f"upadan_{i}",
            section=f"{i}A", court=f"court_{i}"
        )
        gold_ans = f"প্রমাণিত_উত্তর_{i}"
        ev_text = (
            f"এটি সিন্থেটিক পরীক্ষার প্রমাণ {i}। ডোমেইন: {domain}। "
            f"প্রশ্নের সঠিক ও সুস্পষ্ট উত্তর হলো {gold_ans}। "
            f"উক্ত তথ্যের নির্ভুলতা এই অনুচ্ছেদে নিশ্চিত করা হয়েছে এবং বিস্তারিত ব্যাখ্যা রয়েছে।"
        )

        item = {
            "schema_version": SCHEMA_VERSION,
            "item_id": item_id,
            "domain": domain,
            "question_bn": bn_q,
            "question_banglish": banglish_q,
            "gold_answer": gold_ans,
            "evidence_id": ev_id,
            "answer_type": answer_type,
            "risk_tag": risk_tag,
            "split": split,
            "group_key": group_key,
        }
        items.append(item)

        evidence = {
            "schema_version": SCHEMA_VERSION,
            "evidence_id": ev_id,
            "text": ev_text,
            "source_url_or_id": f"https://synthetic.example.org/{ev_id}",
            "source_date": "2026-01-01",
            "domain": domain,
        }
        evidences.append(evidence)

        # Corpus gold passage
        corpus_passages.append({
            "schema_version": SCHEMA_VERSION,
            "passage_id": ev_id,
            "text": ev_text,
            "source_url_or_id": f"https://synthetic.example.org/{ev_id}",
            "source_date": "2026-01-01",
            "domain": domain,
            "is_gold_for": [item_id],
        })

    # 2. Generate Distractor Corpus Passages (~1000)
    for k in range(1, n_distractors + 1):
        pass_id = f"cp_syn_{k:04d}"
        domain = DOMAINS[(k - 1) % len(DOMAINS)]
        text = (
            f"সিন্থেটিক ডিস্ট্রাক্টর অনুচ্ছেদ {k} ({domain})। "
            f"বাংলাদেশ ও সংশ্লিষ্ট প্রসঙ্গের সাধারণ তথ্যাবলী এখানে বর্ণিত হয়েছে। "
            f"এই অনুচ্ছেদে কোনো নির্দিষ্ট গোল্ড প্রশ্নের উত্তর নেই, এটি প্রাসঙ্গিক ব্যাকগ্রাউন্ড টেক্সট।"
        )
        corpus_passages.append({
            "schema_version": SCHEMA_VERSION,
            "passage_id": pass_id,
            "text": text,
            "source_url_or_id": f"https://synthetic.example.org/{pass_id}",
            "source_date": "2026-01-01",
            "domain": domain,
            "is_gold_for": [],
        })

    # Write JSONL files
    with open(items_path, "w", encoding="utf-8") as f:
        for r in items:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(evidence_path, "w", encoding="utf-8") as f:
        for r in evidences:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(corpus_path, "w", encoding="utf-8") as f:
        for r in corpus_passages:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Generated {len(items)} synthetic items: {items_path}")
    print(f"Generated {len(evidences)} synthetic evidences: {evidence_path}")
    print(f"Generated {len(corpus_passages)} synthetic corpus passages: {corpus_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic stress test dataset")
    parser.add_argument("--output-dir", type=Path, default=Path("data/synthetic_stress"))
    parser.add_argument("--items", type=int, default=100)
    parser.add_argument("--distractors", type=int, default=1000)
    args = parser.parse_args()

    generate_stress_data(args.output_dir, args.items, args.distractors)


if __name__ == "__main__":
    main()
