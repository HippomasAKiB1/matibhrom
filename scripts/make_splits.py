"""
Write derived convenience split files under data/splits/.

The `split` field on each `Item` is the source of truth (README §3.4). This
script never assigns or changes splits — it only reads the authoritative
`split` field from items.jsonl and writes dev.jsonl / test.jsonl as a
convenience for tools that want to iterate one split without re-filtering.

Usage:
    python scripts/make_splits.py --items data/dummy/items.jsonl --out-dir data/splits
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.schema import Item
from src.validate_data import load_jsonl


def make_splits(items_path: Path, out_dir: Path) -> dict[str, int]:
    """Read items, group by their authoritative `split` field, and write
    data/splits/{split}.jsonl. Returns counts per split."""
    raw = load_jsonl(items_path)
    items = [Item.model_validate(r) for r in raw]

    by_split: dict[str, list[Item]] = defaultdict(list)
    for item in items:
        by_split[item.split].append(item)

    # Sanity check: items sharing a group_key (or, absent that, an
    # evidence_id) must not straddle splits (README §3.4 "grouped split").
    group_to_splits: dict[str, set[str]] = defaultdict(set)
    for item in items:
        key = item.group_key or item.evidence_id
        group_to_splits[key].add(item.split)

    violations = {k: v for k, v in group_to_splits.items() if len(v) > 1}
    if violations:
        msg = "\n".join(f"  - group {k!r} spans splits {sorted(v)}" for k, v in violations.items())
        raise ValueError(f"Grouped-split invariant violated:\n{msg}")

    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for split_name, split_items in by_split.items():
        out_path = out_dir / f"{split_name}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for item in split_items:
                f.write(json.dumps(item.model_dump(), ensure_ascii=False) + "\n")
        counts[split_name] = len(split_items)

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Write derived data/splits/*.jsonl from items.jsonl")
    parser.add_argument("--items", default="data/dummy/items.jsonl", help="Path to items.jsonl")
    parser.add_argument("--out-dir", default="data/splits", help="Output directory for split files")
    args = parser.parse_args()

    counts = make_splits(Path(args.items), Path(args.out_dir))
    print("Wrote derived splits (source of truth remains the `split` field on each Item):")
    for split_name, n in sorted(counts.items()):
        print(f"  {split_name}: {n} items -> {args.out_dir}/{split_name}.jsonl")


if __name__ == "__main__":
    main()
