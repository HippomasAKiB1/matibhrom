"""
Core generation loop for Matibhrom.
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.schema import Item, Generation, RetrievalLog
from src.prompts.builder import PromptBuilder
from src.hashing import hash_prompt
from src.model_adapters import get_adapter_class
from src.runner.cache import GenerationCache
from src.runner.locks import create_lock_atomic, release_lock, remove_lock, LockError
from src.io_atomic import write_jsonl_atomic
from src.runner.logging_utils import get_logger

logger = get_logger(__name__)


class GenerationRunner:
    """Core runner that orchestrates generation across all conditions."""

    def __init__(
        self,
        run_id: str,
        items: list[Item],
        languages: list[str],
        conditions: list[str],
        models: list[dict],
        prompt_builder: PromptBuilder,
        cache: GenerationCache,
        retriever: Any | None = None,
        output_dir: str | Path = "outputs",
    ):
        self.run_id = run_id
        self.items = items
        self.languages = languages
        self.conditions = conditions
        self.models = models
        self.prompt_builder = prompt_builder
        self.cache = cache
        self.retriever = retriever
        self.output_dir = Path(output_dir)
        self.generated_count = 0
        self.retrieval_logs: list[RetrievalLog] = []

        # Ensure output directories exist
        self.generations_dir = self.output_dir / run_id / "generations"
        self.generations_dir.mkdir(parents=True, exist_ok=True)

        self.retrieval_dir = self.output_dir / run_id / "retrieval"
        self.retrieval_dir.mkdir(parents=True, exist_ok=True)

        self.locks_dir = self.output_dir / run_id / "locks"
        self.locks_dir.mkdir(parents=True, exist_ok=True)

    def _generate_generation_id(self, item_id: str, language: str, condition: str, model_id: str) -> str:
        """Generate deterministic generation ID."""
        payload = f"{self.run_id}|{item_id}|{language}|{condition}|{model_id}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def _get_model_params(self, model_config: dict) -> dict:
        """Get generation parameters for a model."""
        return model_config.get("params", {})

    def _get_model_version(self, model_config: dict, adapter_name: str) -> str:
        """Get model version string."""
        return f"{adapter_name}-1.0"

    def _get_retrieval_for(self, item: Item, language: str, question: str, cache: dict) -> tuple[list[dict], str]:
        """Retrieve (once) for this (item, language), memoizing in `cache` and
        emitting exactly one RetrievalLog record — reused by both C2 and C3
        for the same item/language so their context is byte-identical
        (§8.10/§12), and never re-retrieved per model."""
        if "retrieved" in cache:
            return cache["retrieved"], cache["context"]

        retrieved, gold_retrieved, recall_at_k = self.retriever.retrieve_for_item(
            item_id=item.item_id, question=question, evidence_id=item.evidence_id
        )
        context = self.retriever.build_context(retrieved)
        cache["retrieved"] = retrieved
        cache["context"] = context

        log = RetrievalLog(
            run_id=self.run_id,
            item_id=item.item_id,
            language=language,
            query=question,
            query_hash=hash_prompt(question),
            top_k=self.retriever.top_k,
            retrieved=[
                {
                    "rank": p["rank"],
                    "passage_id": p["passage_id"],
                    "evidence_id": p["evidence_id"],
                    "score": p["score"],
                    "text": p["text"],
                }
                for p in retrieved
            ],
            gold_evidence_id=item.evidence_id,
            gold_retrieved=gold_retrieved,
            recall_at_k=recall_at_k,
            index_version=getattr(self.retriever, "index_version", ""),
            corpus_version=getattr(self.retriever, "corpus_version", ""),
        )
        self.retrieval_logs.append(log)
        write_jsonl_atomic(str(self.retrieval_dir / "retrieval_logs.jsonl"), log.model_dump())

        return retrieved, context

    def generate_all(self) -> list[Generation]:
        """
        Run generation across all items, languages, conditions, and models.

        Returns:
            List of Generation objects created.
        """
        generations = []

        for item in self.items:
            for language in self.languages:
                question = item.question_bn if language == "bn" else item.question_banglish
                retrieval_cache: dict = {}

                for condition in self.conditions:
                    for model_config in self.models:
                        model_id = model_config["id"]
                        adapter_name = model_config["adapter"]
                        params = model_config.get("params", {})

                        # Build prompt + evidence_ids_used (§9.10):
                        #   C0 -> []
                        #   C1 -> [item.evidence_id]
                        #   C2 -> deduplicated, order-preserving evidence_ids from retrieval
                        #   C3 -> identical to C2 for the same (item, language)
                        if condition == "C0":
                            evidence_ids_used: list[str] = []
                            prompt, template_name = self.prompt_builder.build_prompt(
                                item=item, language=language, condition=condition
                            )
                        elif condition == "C1":
                            evidence = self._get_evidence(item)
                            evidence_ids_used = [item.evidence_id]
                            prompt, template_name = self.prompt_builder.build_prompt(
                                item=item, language=language, condition=condition, evidence=evidence
                            )
                        elif condition in ("C2", "C3"):
                            if self.retriever is None:
                                logger.warning(f"No retriever for {condition}, skipping")
                                continue
                            retrieved, retrieved_context = self._get_retrieval_for(
                                item, language, question, retrieval_cache
                            )
                            seen: set[str] = set()
                            evidence_ids_used = []
                            for p in retrieved:
                                if p["evidence_id"] not in seen:
                                    seen.add(p["evidence_id"])
                                    evidence_ids_used.append(p["evidence_id"])
                            prompt, template_name = self.prompt_builder.build_prompt(
                                item=item, language=language, condition=condition,
                                retrieved_context=retrieved_context
                            )
                        else:
                            raise ValueError(f"Unknown condition: {condition}")

                        # Check cache
                        model_version = self._get_model_version(model_config, adapter_name)
                        cache_key = self.cache._make_cache_key(
                            prompt=prompt, model_id=model_id, model_version=model_version,
                            temperature=params.get("temperature", 0.0),
                            max_tokens=params.get("max_tokens", 512),
                            seed=params.get("seed", 42)
                        )

                        cached = self.cache.get(cache_key, self.cache.SCHEMA_VERSION)
                        if cached:
                            logger.info(f"Cache hit for {cache_key[:8]}...")
                            generations.append(self._create_generation_from_cache(
                                cached, item, language, condition, model_id, model_version, evidence_ids_used
                            ))
                            continue

                        generation_id = self._generate_generation_id(
                            item.item_id, language, condition, model_id
                        )

                        # Resumability: a lock file per generation_id claims the
                        # work. If it already exists another (possibly earlier,
                        # crashed) process already produced (or is producing)
                        # this generation, so skip rather than duplicate it.
                        lock_path = self.locks_dir / f"{generation_id}.lock"
                        try:
                            lock_fd = create_lock_atomic(lock_path)
                        except LockError:
                            logger.info(f"Generation {generation_id} already claimed, skipping")
                            continue

                        try:
                            adapter_cls = get_adapter_class(adapter_name)
                            adapter = adapter_cls(model_id=model_id, params=params)
                            result = adapter.generate(prompt)

                            resolved_model_version = result.model_version or model_version
                            timestamp = datetime.now(timezone.utc).isoformat()

                            generation = Generation(
                                run_id=self.run_id,
                                generation_id=generation_id,
                                item_id=item.item_id,
                                language=language,
                                condition=condition,
                                model_id=model_id,
                                model_version=resolved_model_version,
                                prompt=prompt,
                                prompt_hash=hash_prompt(prompt),
                                prompt_tokens=result.prompt_tokens,
                                response=result.text,
                                response_tokens=result.response_tokens,
                                evidence_ids_used=evidence_ids_used,
                                temperature=params.get("temperature", 0.0),
                                seed=params.get("seed", 42),
                                max_tokens=params.get("max_tokens", 512),
                                timestamp=timestamp,
                                latency_ms=result.latency_ms,
                                cost_usd=result.cost_usd,
                                error=result.error,
                            )

                            self.cache.put(
                                key=cache_key,
                                generation_id=generation_id,
                                response=result.text,
                                model_version=resolved_model_version,
                                config_hash="",
                                timestamp=timestamp,
                            )

                            generations.append(generation)
                            self.generated_count += 1
                        finally:
                            release_lock(lock_fd)
                            remove_lock(lock_path)

                    logger.info(f"Processed item {item.item_id}, language {language}, condition {condition}")

        return generations

    def _get_evidence(self, item: Item) -> str:
        """Get chunk-matched evidence for C1 (§8.10)."""
        if self.retriever is None:
            return ""
        evidence_chunks = self.retriever.get_evidence_chunks(item.evidence_id)
        return self.retriever.build_context(evidence_chunks)

    def _create_generation_from_cache(
        self, cached, item, language, condition, model_id, model_version, evidence_ids_used: list[str] | None = None
    ) -> Generation:
        """Create a Generation object from cached data."""
        return Generation(
            run_id=self.run_id,
            generation_id=cached.generation_id,
            item_id=item.item_id,
            language=language,
            condition=condition,
            model_id=model_id,
            model_version=model_version,
            prompt="",  # Not stored in cache, reconstructed on demand
            prompt_hash="",
            prompt_tokens=0,
            response=cached.response,
            response_tokens=len(cached.response.split()),
            evidence_ids_used=evidence_ids_used or [],
            temperature=0.0,
            seed=42,
            max_tokens=512,
            timestamp=cached.timestamp,
            latency_ms=None,
            cost_usd=None
        )
