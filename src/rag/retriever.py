"""
Retriever for Matibhrom RAG.
"""

import logging
from pathlib import Path
from typing import Any

from src.rag.embedder import Embedder
from src.rag.index import Index
from src.rag.chunker import Chunker

logger = logging.getLogger(__name__)


class Retriever:
    """RAG retriever using FAISS + embeddings."""

    def __init__(
        self,
        corpus_path: str | Path,
        index_dir: str | Path,
        embedding_model: str = "BAAI/bge-m3",
        top_k: int = 5,
        chunk_size: int = 384,
        chunk_overlap: int = 64,
    ):
        self.corpus_path = Path(corpus_path)
        self.index_dir = Path(index_dir)
        self.embedding_model = embedding_model
        self.top_k = top_k
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self._index = None
        self._embedder = None
        self._corpus_data = None
        self._passage_ids = None
        self._chunker = None

    def _load_corpus(self) -> list[dict]:
        """Load corpus passages from JSONL."""
        if self._corpus_data is None:
            import json
            passages = []
            with open(self.corpus_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        passages.append(json.loads(line))
            self._corpus_data = passages
        return self._corpus_data

    def _load_embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = Embedder(self.embedding_model)
        return self._embedder

    def _load_index(self) -> Index:
        if self._index is None:
            self._index = Index()
            self._index.load(self.index_dir)
        return self._index

    @property
    def index_version(self) -> str:
        return self._load_index().metadata.index_version

    @property
    def corpus_version(self) -> str:
        return self._load_index().metadata.corpus_version

    def _load_chunker(self) -> Chunker:
        if self._chunker is None:
            self._chunker = Chunker(self.chunk_size, self.chunk_overlap)
        return self._chunker

    def retrieve(self, query: str, top_k: int | None = None) -> list[dict]:
        """
        Retrieve top-k passages for a query.

        Args:
            query: The query text
            top_k: Number of passages to retrieve (defaults to self.top_k)

        Returns:
            List of RetrievedPassage dicts
        """
        k = top_k if top_k is not None else self.top_k

        embedder = self._load_embedder()
        index = self._load_index()
        corpus = self._load_corpus()

        # Encode query
        query_embedding = embedder.encode_single(query)

        # Search
        scores, indices = index.search(query_embedding, k)

        # Get passage data
        results = []
        for rank, (score, idx) in enumerate(zip(scores, indices)):
            if idx >= 0 and idx < len(corpus):
                passage = corpus[idx]
                results.append({
                    "rank": rank + 1,
                    "passage_id": passage["passage_id"],
                    "score": float(score),
                    "text": passage["text"],
                    "evidence_id": passage["passage_id"],  # For gold matching
                })

        return results

    def retrieve_for_item(
        self,
        item_id: str,
        question: str,
        evidence_id: str,
        top_k: int | None = None
    ) -> tuple[list[dict], bool, float]:
        """
        Retrieve passages for an item and check if gold evidence was retrieved.

        Args:
            item_id: Item ID
            question: The question text (used as query)
            evidence_id: The gold evidence ID
            top_k: Number of passages to retrieve

        Returns:
            (retrieved_passages, gold_retrieved, recall_at_k)
        """
        k = top_k if top_k is not None else self.top_k
        retrieved = self.retrieve(question, k)

        gold_retrieved = any(
            p["passage_id"] == evidence_id or p["evidence_id"] == evidence_id
            for p in retrieved
        )
        recall_at_k = 1.0 if gold_retrieved else 0.0

        return retrieved, gold_retrieved, recall_at_k

    def get_evidence_chunks(self, evidence_id: str, top_k: int | None = None) -> list[dict]:
        """
        Get the chunk-matched evidence for C1 condition (§8.10).

        This returns the same chunks that the retriever would return if given
        the gold evidence_id as the query, capped at top_k and max_input_tokens.

        Args:
            evidence_id: The gold evidence ID
            top_k: Maximum number of chunks to return

        Returns:
            List of RetrievedPassage dicts
        """
        k = top_k if top_k is not None else self.top_k
        corpus = self._load_corpus()

        # Find the gold evidence passage
        gold_passage = None
        for p in corpus:
            if p["passage_id"] == evidence_id:
                gold_passage = p
                break

        if gold_passage is None:
            return []

        # Chunk the gold evidence using the same chunker
        chunker = self._load_chunker()
        chunks = chunker.chunk_text(gold_passage["text"], gold_passage["passage_id"])

        # Take first top_k chunks in document order
        selected = chunks[:k]

        # Build RetrievedPassage dicts
        results = []
        for i, chunk in enumerate(selected):
            chunk_id = chunker.get_chunk_id(gold_passage["passage_id"], chunk.chunk_index)
            results.append({
                "rank": i + 1,
                "passage_id": chunk_id,
                "score": 1.0,  # Oracle evidence is always "retrieved"
                "text": chunk.text,
                "evidence_id": evidence_id,
            })

        return results

    def build_context(self, retrieved: list[dict], max_tokens: int | None = None) -> str:
        """
        Build the retrieved_context string for C2/C3 prompts.

        Each passage is prefixed with [Passage {i}].

        Args:
            retrieved: List of RetrievedPassage dicts
            max_tokens: Maximum tokens for the context (truncates if needed)

        Returns:
            Formatted context string
        """
        parts = []
        for p in retrieved:
            parts.append(f"[Passage {p['rank']}] {p['text']}")

        context = "\n".join(parts)

        if max_tokens is not None:
            # Truncate if too long
            words = context.split()
            if len(words) > max_tokens:
                context = " ".join(words[:max_tokens])

        return context