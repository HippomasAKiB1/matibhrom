"""
Annotation storage for Matibhrom: immediate-save JSONL + SQLite mirror
(README §14.3 "immediate save to JSONL + SQLite mirror").

The JSONL file is the source of truth (consistent with every other artifact
in this project); the SQLite mirror exists purely so the Streamlit UI can do
fast lookups (by generation_id, by annotator, "next unannotated") without
re-scanning a growing JSONL file on every interaction.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

from src.io_atomic import write_jsonl_atomic
from src.schema import Adjudication, Annotation


class AnnotationStore:
    """JSONL-of-record + SQLite-mirror storage for Annotation and
    Adjudication records, one store per run."""

    def __init__(self, run_dir: str | Path):
        self.run_dir = Path(run_dir)
        self.annotations_path = self.run_dir / "annotations" / "annotations.jsonl"
        self.adjudications_path = self.run_dir / "annotations" / "adjudications.jsonl"
        self.db_path = self.run_dir / "annotations" / "annotations_mirror.db"

        self.annotations_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path), timeout=30)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()
        self._load_existing_jsonl()

    def _create_tables(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS annotations (
                generation_id TEXT NOT NULL,
                annotator_id TEXT NOT NULL,
                labeler_type TEXT,
                correctness TEXT,
                hallucination TEXT,
                error_type TEXT,
                abstention_status TEXT,
                tier2_abstention_candidate INTEGER,
                notes TEXT,
                timestamp TEXT,
                is_overlap INTEGER,
                verified_by_human INTEGER,
                codebook_version TEXT,
                PRIMARY KEY (generation_id, annotator_id)
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS adjudications (
                generation_id TEXT PRIMARY KEY,
                adjudicator_id TEXT,
                final_correctness TEXT,
                final_hallucination TEXT,
                final_error_type TEXT,
                rationale TEXT,
                timestamp TEXT,
                codebook_version TEXT
            )
        """)
        self.conn.commit()

    def _load_existing_jsonl(self) -> None:
        """On startup, replay any existing JSONL records into the SQLite
        mirror (e.g. if the mirror was deleted, or this is a fresh checkout
        of a run someone else annotated)."""
        if self.annotations_path.exists():
            with open(self.annotations_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self._mirror_annotation(Annotation.model_validate(json.loads(line)))
        if self.adjudications_path.exists():
            with open(self.adjudications_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self._mirror_adjudication(Adjudication.model_validate(json.loads(line)))

    def _mirror_annotation(self, ann: Annotation) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO annotations
            (generation_id, annotator_id, labeler_type, correctness, hallucination,
             error_type, abstention_status, tier2_abstention_candidate, notes,
             timestamp, is_overlap, verified_by_human, codebook_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ann.generation_id, ann.annotator_id, ann.labeler_type, ann.correctness,
                ann.hallucination, ann.error_type, ann.abstention_status,
                int(ann.tier2_abstention_candidate), ann.notes, ann.timestamp,
                int(ann.is_overlap), int(ann.verified_by_human), ann.codebook_version,
            ),
        )
        self.conn.commit()

    def _mirror_adjudication(self, adj: Adjudication) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO adjudications
            (generation_id, adjudicator_id, final_correctness, final_hallucination,
             final_error_type, rationale, timestamp, codebook_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                adj.generation_id, adj.adjudicator_id, adj.final_correctness,
                adj.final_hallucination, adj.final_error_type, adj.rationale,
                adj.timestamp, adj.codebook_version,
            ),
        )
        self.conn.commit()

    def save_annotation(self, annotation: Annotation) -> None:
        """Immediate save: append to JSONL (source of truth), then mirror
        into SQLite for fast UI queries."""
        write_jsonl_atomic(str(self.annotations_path), annotation.model_dump())
        self._mirror_annotation(annotation)

    def save_adjudication(self, adjudication: Adjudication) -> None:
        write_jsonl_atomic(str(self.adjudications_path), adjudication.model_dump())
        self._mirror_adjudication(adjudication)

    def get_annotations_for_generation(self, generation_id: str) -> list[dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM annotations WHERE generation_id = ? ORDER BY timestamp",
            (generation_id,),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def get_annotation_by_annotator(self, generation_id: str, annotator_id: str) -> dict[str, Any] | None:
        cur = self.conn.execute(
            "SELECT * FROM annotations WHERE generation_id = ? AND annotator_id = ?",
            (generation_id, annotator_id),
        )
        row = cur.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))

    def annotated_generation_ids(self, annotator_id: str | None = None) -> set[str]:
        if annotator_id is not None:
            cur = self.conn.execute(
                "SELECT DISTINCT generation_id FROM annotations WHERE annotator_id = ?",
                (annotator_id,),
            )
        else:
            cur = self.conn.execute("SELECT DISTINCT generation_id FROM annotations")
        return {row[0] for row in cur.fetchall()}

    def disagreements_in_overlap(self) -> list[dict[str, Any]]:
        """Find generation_ids with >=2 annotations on `hallucination` that
        disagree — used to drive the adjudication trigger (§14.5/§14.6)."""
        cur = self.conn.execute(
            "SELECT generation_id, hallucination, COUNT(DISTINCT hallucination) as n_distinct "
            "FROM annotations WHERE is_overlap = 1 AND hallucination IS NOT NULL "
            "GROUP BY generation_id HAVING n_distinct > 1"
        )
        return [{"generation_id": row[0]} for row in cur.fetchall()]

    def close(self) -> None:
        self.conn.close()
