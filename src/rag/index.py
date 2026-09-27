"""
FAISS vector index for Matibhrom RAG.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

import faiss
import numpy as np

logger = logging.getLogger(__name__)


class CorpusMetadata:
    """Metadata about the indexed corpus."""
    def __init__(
        self,
        corpus_version: str = "",
        index_version: str = "",
        n_passages: int = 0,
        embedding_dim: int = 768
    ):
        self.corpus_version = corpus_version
        self.index_version = index_version
        self.n_passages = n_passages
        self.embedding_dim = embedding_dim

    def __repr__(self):
        return f"CorpusMetadata(n={self.n_passages}, dim={self.embedding_dim}, versions={[self.corpus_version, self.index_version]})"


class Index:
    """FAISS vector index for RAG retrieval."""

    def __init__(self, embedding_dim: int = 768, index_type: str = "IndexFlatIP"):
        self.embedding_dim = embedding_dim
        self.index_type = index_type
        self._index = None
        self._metadata = CorpusMetadata()
        self._passage_ids = []
        self._file_paths = []

    @property
    def index(self):
        if self._index is None:
            self._index = faiss.IndexFlatIP(self.embedding_dim)
        return self._index

    @property
    def metadata(self) -> CorpusMetadata:
        return self._metadata

    def build(self, embeddings: np.ndarray, passage_ids: list[str]) -> None:
        """
        Build the FAISS index from embeddings.

        Args:
            embeddings: numpy array of shape (n, embedding_dim)
            passage_ids: List of passage IDs corresponding to each embedding
        """
        if embeddings.shape[1] != self.embedding_dim:
            raise ValueError(
                f"Embedding dimension {embeddings.shape[1]} != expected {self.embedding_dim}"
            )

        self.index.add(embeddings.astype("float32"))
        self._passage_ids = passage_ids
        self._metadata = CorpusMetadata(
            corpus_version="",
            index_version="",
            n_passages=len(passage_ids),
            embedding_dim=self.embedding_dim
        )
        logger.info(f"Built FAISS index with {len(passage_ids)} passages")

    def search(self, query_embedding: np.ndarray, k: int = 5) -> tuple[list[float], list[int]]:
        """
        Search for top-k similar passages.

        Args:
            query_embedding: Query embedding vector
            k: Number of results to return

        Returns:
            (scores, indices) where scores are cosine similarity and indices are into the index
        """
        if self.index.ntotal == 0:
            raise RuntimeError("Index is empty. Build the index first.")

        # Ensure float32
        query = query_embedding.reshape(1, -1).astype("float32")

        distances, indices = self.index.search(query, k)

        return distances.tolist()[0], indices.tolist()[0]

    def save(self, index_dir: str | Path, index_version: str | None = None) -> None:
        """
        Save the FAISS index and metadata to disk.

        Args:
            index_dir: Directory to save to
            index_version: Version string (defaults to timestamp)
        """
        index_dir = Path(index_dir)
        index_dir.mkdir(parents=True, exist_ok=True)

        # Save the index
        index_path = index_dir / "index.faiss"
        faiss.write_index(self.index, str(index_path))

        # Save metadata
        import json
        metadata = {
            "corpus_version": self._metadata.corpus_version,
            "index_version": index_version or "",
            "n_passages": self._metadata.n_passages,
            "embedding_dim": self._metadata.embedding_dim,
        }
        metadata_path = index_dir / "index_metadata.json"
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

        # Save passage IDs
        ids_path = index_dir / "passage_ids.json"
        ids_path.write_text(json.dumps(self._passage_ids), encoding="utf-8")

        logger.info(f"Saved FAISS index to {index_dir}")

    def load(self, index_dir: str | Path) -> None:
        """
        Load the FAISS index and metadata from disk.

        Args:
            index_dir: Directory to load from
        """
        index_dir = Path(index_dir)

        # Load metadata
        metadata_path = index_dir / "index_metadata.json"
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            self._metadata = CorpusMetadata(**metadata)

        # Load passage IDs
        ids_path = index_dir / "passage_ids.json"
        if ids_path.exists():
            self._passage_ids = json.loads(ids_path.read_text(encoding="utf-8"))

        # Load the index
        index_path = index_dir / "index.faiss"
        if index_path.exists():
            self._index = faiss.read_index(str(index_path))

        logger.info(f"Loaded FAISS index from {index_dir}")

    def get_retrieved_passages(
        self,
        corpus_data: list[dict],
        indices: list[int]
    ) -> list[dict]:
        """
        Get the actual passage data for retrieved indices.

        Args:
            corpus_data: List of corpus passage dicts
            indices: List of indices into corpus_data

        Returns:
            List of RetrievedPassage dicts with rank, passage_id, score, text
        """
        results = []
        for rank, idx in enumerate(indices):
            if idx >= 0 and idx < len(corpus_data):
                passage = corpus_data[idx]
                results.append({
                    "rank": rank + 1,
                    "passage_id": passage["passage_id"],
                    "score": 1.0,  # FAISS distances are normalized
                    "text": passage["text"]
                })
        return results