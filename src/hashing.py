"""
Hashing utilities for Matibhrom reproducibility system.
All hashes are SHA256 truncated to 16 hex characters, stored as lowercase strings.
"""

import hashlib
from pathlib import Path

import yaml


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def hash_prompt(text: str) -> str:
    """Hash a rendered prompt string (used for Generation.prompt_hash)."""
    return _sha256_hex(text.encode("utf-8"))


def hash_config(paths: list[str | Path]) -> str:
    """Hash a list of config file paths concatenated."""
    digest = hashlib.sha256()
    for p in sorted(paths):
        digest.update(Path(p).read_bytes())
    return digest.hexdigest()[:16]


def hash_corpus(corpus_path: str | Path, chunk_config: dict, embedding_model: str) -> str:
    """Hash corpus file + chunk config + embedding model."""
    digest = hashlib.sha256()
    digest.update(Path(corpus_path).read_bytes())
    digest.update(str(chunk_config).encode("utf-8"))
    digest.update(embedding_model.encode("utf-8"))
    return digest.hexdigest()[:16]


def hash_template(text: str) -> str:
    """Hash a prompt template file's contents."""
    return _sha256_hex(text.encode("utf-8"))


def hash_model_version(model_id: str, revision: str) -> str:
    """Hash model ID and revision."""
    payload = f"{model_id}@{revision}"
    return _sha256_hex(payload.encode("utf-8"))


def hash_cache_key(
    prompt: str,
    model_id: str,
    model_version: str,
    temperature: float,
    max_tokens: int,
    seed: int | None,
) -> str:
    """Stable cache key function across processes and machines."""
    payload = "|".join([
        prompt, model_id, model_version,
        str(temperature), str(max_tokens), str(seed),
    ])
    return _sha256_hex(payload.encode("utf-8"))
