"""
Build the frozen FAISS retrieval index for C2/C3 RAG conditions.

Reads configs/rag.yaml, chunks the corpus, embeds every chunk, and writes
the FAISS index plus its metadata (`index_version`, `corpus_version`) under
outputs/{run_id}/retrieval/index/. Must be re-run whenever the corpus or
chunking configuration changes (README §12.1) — the index is a frozen
precondition for the main run, so `run.py`'s pre-flight checks and the C2/C3
byte-identical-context test both depend on this having been run first.

Usage:
    python scripts/build_index.py --config configs/rag.yaml --run-id main_v1
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml

from src.hashing import hash_corpus
from src.rag.chunker import chunk_corpus
from src.rag.embedder import Embedder
from src.rag.index import Index
from src.validate_data import load_jsonl


def build_index(rag_config: dict, run_id: str, min_corpus_passages: int | None = None) -> Path:
    corpus_path = Path(rag_config["corpus_path"])
    chunk_size = rag_config.get("chunk_size", 384)
    chunk_overlap = rag_config.get("chunk_overlap", 64)
    embedding_model = rag_config.get("embedding_model", "BAAI/bge-m3")
    min_passages = min_corpus_passages if min_corpus_passages is not None else rag_config.get("min_corpus_passages", 1000)

    corpus = load_jsonl(corpus_path)
    if len(corpus) < min_passages:
        raise ValueError(
            f"Corpus has {len(corpus)} passages, minimum is {min_passages} "
            f"(configs/rag.yaml: min_corpus_passages). Refusing to build a frozen index."
        )

    print(f"Chunking {len(corpus)} corpus passages (chunk_size={chunk_size}, overlap={chunk_overlap})...")
    chunks = chunk_corpus(corpus, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    print(f"Produced {len(chunks)} chunks.")

    print(f"Embedding chunks with {embedding_model}...")
    embedder = Embedder(embedding_model)
    texts = [c["text"] for c in chunks]
    embeddings = embedder.encode(texts)

    index = Index(embedding_dim=embeddings.shape[1])
    index.build(embeddings, passage_ids=[c["passage_id"] for c in chunks])

    corpus_version = hash_corpus(
        corpus_path,
        {"chunk_size": chunk_size, "chunk_overlap": chunk_overlap},
        embedding_model,
    )
    index_version = f"idx_{int(time.time())}_{corpus_version}"
    index._metadata.corpus_version = corpus_version

    index_dir_template = rag_config.get("index_dir", "outputs/{run_id}/retrieval/index")
    index_dir = Path(index_dir_template.format(run_id=run_id))
    index.save(index_dir, index_version=index_version)

    # Also persist the chunked corpus itself so the retriever's corpus lookups
    # (by chunk passage_id) line up 1:1 with what was embedded/indexed.
    chunked_corpus_path = index_dir / "chunked_corpus.jsonl"
    with open(chunked_corpus_path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"corpus_version={corpus_version}")
    print(f"index_version={index_version}")
    print(f"Saved index to {index_dir}")
    return index_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the frozen FAISS retrieval index")
    parser.add_argument("--config", default="configs/rag.yaml", help="Path to rag.yaml")
    parser.add_argument("--run-id", required=True, help="Run ID (used to namespace the index directory)")
    parser.add_argument("--min-corpus-passages", type=int, help="Override min_corpus_passages guard")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        rag_config = yaml.safe_load(f)

    build_index(rag_config, args.run_id, args.min_corpus_passages)


if __name__ == "__main__":
    main()
