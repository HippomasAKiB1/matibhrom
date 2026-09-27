"""
Schema migration for Matibhrom JSONL records (README §9.1).

Every JSONL record carries `schema_version`. On startup, the runner and
validator require all input records to match the current `SCHEMA_VERSION`
(src/schema_version.py). If a record was produced under an older schema
version, it must be migrated with this script before it can be used.

As of this writing there is only ever one schema version (1.0.0) in the
wild, so there are no migrations registered yet — this is the harness the
README asks for ("write on demand"), ready for the first time
SCHEMA_VERSION is bumped.

Usage:
    # Report the schema_version distribution in a file, without changing it:
    python scripts/migrate_schema.py check data/dummy/items.jsonl

    # Migrate a file's records up to the current SCHEMA_VERSION in place
    # (writes a new file; never overwrites the input):
    python scripts/migrate_schema.py migrate data/dummy/items.jsonl \
        --record-type item --output data/dummy/items.migrated.jsonl

To add a migration when SCHEMA_VERSION is bumped: write a function
`(record: dict) -> dict` that upgrades one record from version A to the
next version, and register it in MIGRATIONS[record_type][A]. Migrations
are applied in a chain (A -> B -> C -> ...) until the record reaches
`SCHEMA_VERSION`.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.schema import (
    Adjudication, Annotation, CorpusPassage, Evidence, Generation, Item, RetrievalLog,
)
from src.schema_version import SCHEMA_VERSION
from src.validate_data import load_jsonl

RECORD_TYPES = {
    "item": Item,
    "evidence": Evidence,
    "corpus": CorpusPassage,
    "generation": Generation,
    "retrieval_log": RetrievalLog,
    "annotation": Annotation,
    "adjudication": Adjudication,
}

# MIGRATIONS[record_type][from_version] = function(dict) -> dict (record at
# the *next* version). Empty until SCHEMA_VERSION is first bumped past 1.0.0.
MIGRATIONS: dict[str, dict[str, "callable"]] = {name: {} for name in RECORD_TYPES}


def migrate_record(record: dict, record_type: str, target_version: str = SCHEMA_VERSION) -> dict:
    """Apply registered migrations to `record` until it reaches
    `target_version`. Raises if no migration path exists from its current
    version."""
    migrations_for_type = MIGRATIONS.get(record_type, {})
    seen_versions = set()
    while record.get("schema_version") != target_version:
        current = record.get("schema_version")
        if current in seen_versions:
            raise ValueError(f"Migration cycle detected for {record_type} at version {current}")
        seen_versions.add(current)

        migrate_fn = migrations_for_type.get(current)
        if migrate_fn is None:
            raise ValueError(
                f"No migration registered for {record_type} records at schema_version "
                f"{current!r} (target: {target_version!r}). Add one to MIGRATIONS "
                f"in scripts/migrate_schema.py."
            )
        record = migrate_fn(record)
    return record


def cmd_check(args: argparse.Namespace) -> None:
    records = load_jsonl(Path(args.path))
    versions = Counter(r.get("schema_version", "<missing>") for r in records)
    print(f"{len(records)} records in {args.path}")
    for version, count in sorted(versions.items()):
        marker = " (current)" if version == SCHEMA_VERSION else " (NEEDS MIGRATION)"
        print(f"  schema_version={version}: {count} records{marker}")


def cmd_migrate(args: argparse.Namespace) -> None:
    record_type = args.record_type
    if record_type not in RECORD_TYPES:
        print(f"Unknown --record-type {record_type!r}. Choose from: {sorted(RECORD_TYPES)}", file=sys.stderr)
        sys.exit(1)

    model_cls = RECORD_TYPES[record_type]
    records = load_jsonl(Path(args.path))

    output_path = Path(args.output) if args.output else Path(args.path).with_suffix(".migrated.jsonl")
    if output_path == Path(args.path):
        print("Refusing to overwrite the input file. Pass --output to write elsewhere.", file=sys.stderr)
        sys.exit(1)

    n_migrated = 0
    n_unchanged = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            if record.get("schema_version") != SCHEMA_VERSION:
                record = migrate_record(record, record_type)
                n_migrated += 1
            else:
                n_unchanged += 1
            validated = model_cls.model_validate(record)  # re-validate against current schema
            f.write(json.dumps(validated.model_dump(), ensure_ascii=False) + "\n")

    print(f"Wrote {len(records)} records to {output_path} ({n_migrated} migrated, {n_unchanged} already current).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    check_parser = sub.add_parser("check", help="Report schema_version distribution in a JSONL file")
    check_parser.add_argument("path")
    check_parser.set_defaults(func=cmd_check)

    migrate_parser = sub.add_parser("migrate", help="Migrate a JSONL file's records to the current SCHEMA_VERSION")
    migrate_parser.add_argument("path")
    migrate_parser.add_argument("--record-type", required=True, choices=sorted(RECORD_TYPES))
    migrate_parser.add_argument("--output", help="Output path (default: <path>.migrated.jsonl)")
    migrate_parser.set_defaults(func=cmd_migrate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
