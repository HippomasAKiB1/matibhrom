"""
Token-based chunker for Matibhrom RAG.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Chunk:
    """A single chunk of text."""
    passage_id: str
    chunk_index: int
    text: str


class Chunker:
    """Token-based chunker using the embedding model's tokenizer."""

    def __init__(self, chunk_size: int = 384, chunk_overlap: int = 64):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._tokenizer = None

    def _get_tokenizer(self):
        """Get or create the tokenizer for the embedding model."""
        if self._tokenizer is None:
            from transformers import AutoTokenizer
            self._tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-m3")
        return self._tokenizer

    def chunk_text(self, text: str, passage_id: str) -> list[Chunk]:
        """
        Chunk a text into smaller pieces.

        Args:
            text: The text to chunk
            passage_id: The corpus passage ID

        Returns:
            List of Chunk objects
        """
        tokenizer = self._get_tokenizer()
        tokens = tokenizer.encode(text, add_special_tokens=False)

        if len(tokens) <= self.chunk_size:
            return [Chunk(passage_id=passage_id, chunk_index=0, text=text)]

        chunks = []
        start = 0
        chunk_index = 0
        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = tokenizer.decode(chunk_tokens)
            chunks.append(Chunk(
                passage_id=passage_id,
                chunk_index=chunk_index,
                text=chunk_text
            ))
            if end >= len(tokens):
                break
            start = end - self.chunk_overlap
            chunk_index += 1

        return chunks

    def get_chunk_id(self, passage_id: str, chunk_index: int) -> str:
        """Get the chunk ID for a passage and chunk index."""
        if chunk_index == 0:
            return passage_id
        return f"{passage_id}::chunk_{chunk_index}"


def chunk_corpus(passages: list[dict], chunk_size: int = 384, chunk_overlap: int = 64) -> list[dict]:
    """
    Chunk all passages in a corpus.

    Args:
        passages: List of corpus passage dicts
        chunk_size: Maximum tokens per chunk
        chunk_overlap: Overlap between chunks

    Returns:
        List of chunked passage dicts
    """
    chunker = Chunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    result = []
    for passage in passages:
        chunks = chunker.chunk_text(passage["text"], passage["passage_id"])
        for chunk in chunks:
            chunk_id = chunker.get_chunk_id(passage["passage_id"], chunk.chunk_index)
            result.append({
                "passage_id": chunk_id,
                "text": chunk.text,
                "source_url_or_id": passage["source_url_or_id"],
                "source_date": passage["source_date"],
                "domain": passage["domain"],
                "is_gold_for": passage.get("is_gold_for", []),
            })
    return result