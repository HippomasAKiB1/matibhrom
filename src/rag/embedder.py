"""
Embedder for Matibhrom RAG using BAAI/bge-m3.
"""

import gc
import hashlib
import os
import numpy as np
from pathlib import Path
from typing import Any

# Safeguard CPU and memory on developer workstations:
# Restrict PyTorch CPU thread pool so indexing never freezes the OS
try:
    import torch
    if not torch.cuda.is_available():
        max_threads = int(os.environ.get("TORCH_NUM_THREADS", "2"))
        torch.set_num_threads(max_threads)
    max_threads = int(os.environ.get("TORCH_NUM_THREADS", "2"))
    torch.set_num_threads(max_threads)
except Exception:
    pass


class Embedder:
    """Text embedder using sentence-transformers with pure PyTorch fallback."""

    def __init__(self, model_name: str = "BAAI/bge-m3", batch_size: int = 8, device: str = "cpu"):
        self.model_name = model_name
        self.batch_size = batch_size
        self.device = device
        self._model = None

    def _load_model(self):
        """Load the sentence transformer model with resilient pure-Python fallback."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except Exception:
                import torch
                from transformers import AutoTokenizer, AutoModel
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_name, use_fast=False)
                self._hf_model = AutoModel.from_pretrained(self.model_name)
                self._hf_model.eval()
                self._model = "hf_fallback"
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def encode(self, texts: list[str], normalize: bool = True) -> np.ndarray:
        """
        Encode texts into embeddings with progressive memory management.

        Args:
            texts: List of texts to encode
            normalize: Whether to L2 normalize for cosine similarity

        Returns:
            numpy array of shape (n_texts, embedding_dim)
        """
        model = self._load_model()
        
        if model == "hf_fallback":
            import torch
            import torch.nn.functional as F
            inputs = self._tokenizer(texts, padding=True, truncation=True, max_length=512, return_tensors="pt")
            with torch.no_grad():
                out = self._hf_model(**inputs)
                emb = out[0][:, 0]
                if normalize:
                    emb = F.normalize(emb, p=2, dim=1)
            return emb.cpu().numpy().astype("float32")

        # If encoding a large corpus on CPU, batch progressively to avoid memory spikes
        total = len(texts)
        if total > 50:
            embeddings_list = []
            chunk_step = 50
            for start_idx in range(0, total, chunk_step):
                end_idx = min(start_idx + chunk_step, total)
                sub_texts = texts[start_idx:end_idx]
                sub_emb = model.encode(
                    sub_texts,
                    batch_size=self.batch_size,
                    normalize_embeddings=normalize,
                    show_progress_bar=False,
                )
                embeddings_list.append(sub_emb)
                gc.collect()
                print(f"  [Embedder] Encoded {end_idx}/{total} passages...")
            return np.vstack(embeddings_list)
        else:
            embeddings = model.encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=normalize,
                show_progress_bar=False,
            )
            return embeddings

    def encode_single(self, text: str, normalize: bool = True) -> np.ndarray:
        """Encode a single text."""
        return self.encode([text], normalize=normalize)[0]

    def get_cache_key(self, corpus_path: str | Path, chunk_config: dict) -> str:
        """Generate a cache key for embeddings."""
        digest = hashlib.sha256()
        digest.update(Path(corpus_path).read_bytes())
        digest.update(str(chunk_config).encode("utf-8"))
        digest.update(self.model_name.encode("utf-8"))
        return digest.hexdigest()[:16]

    def save_embeddings(self, embeddings: np.ndarray, cache_path: str | Path) -> None:
        """Save embeddings to numpy file."""
        cache_path = Path(cache_path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(cache_path, embeddings)

    def load_embeddings(self, cache_path: str | Path) -> np.ndarray | None:
        """Load embeddings from numpy file."""
        cache_path = Path(cache_path)
        if cache_path.exists():
            return np.load(cache_path)
        return None