"""
Core generation loop for Matibhrom.
"""

import hashlib
import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.schema import Item, Generation, RetrievalLog
from src.prompts.builder import PromptBuilder
from src.hashing import hash_prompt
from src.model_adapters import get_adapter_class
from src.runner.cache import GenerationCache
from src.runner.locks import create_lock_atomic, release_lock, remove_lock, clean_stale_locks, LockError
from src.io_atomic import write_jsonl_atomic, read_jsonl_clean, flush_writer
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
        workers: int = 1,
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
        self.workers = max(1, workers)
        self.generated_count = 0
        self.retrieval_logs: list[RetrievalLog] = []

        self._retrieval_lock = threading.Lock()
        self._generations_lock = threading.Lock()
        self._global_retrieval_cache: dict[tuple[str, str], tuple[list[dict], str]] = {}

        # Ensure output directories exist
        self.generations_dir = self.output_dir / run_id / "generations"
        self.generations_dir.mkdir(parents=True, exist_ok=True)

        self.retrieval_dir = self.output_dir / run_id / "retrieval"
        self.retrieval_dir.mkdir(parents=True, exist_ok=True)

        self.locks_dir = self.output_dir / run_id / "locks"
        self.locks_dir.mkdir(parents=True, exist_ok=True)

        self.generations_path = self.generations_dir / "generations.jsonl"
        self.corrupt_log_path = self.output_dir / run_id / "corrupt_lines.log"

        # Stale lock cleanup (§13.7):
        clean_stale_locks(self.locks_dir)

        # Resumability: index already generated records
        self.existing_generations: dict[str, Generation] = {}
        if self.generations_path.exists():
            records = read_jsonl_clean(self.generations_path, self.corrupt_log_path)
            for r in records:
                try:
                    g = Generation.model_validate(r)
                    self.existing_generations[g.generation_id] = g
                except Exception:
                    pass

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

    def _get_retrieval_for(self, item: Item, language: str, question: str, cache: dict | None = None) -> tuple[list[dict], str]:
        """Retrieve (once) for this (item, language), memoizing thread-safely and
        emitting exactly one RetrievalLog record — reused by both C2 and C3
        for the same item/language so their context is byte-identical
        (§8.10/§12), and never re-retrieved per model."""
        cache_key = (item.item_id, language)
        with self._retrieval_lock:
            if cache_key in self._global_retrieval_cache:
                return self._global_retrieval_cache[cache_key]

            retrieved, gold_retrieved, recall_at_k = self.retriever.retrieve_for_item(
                item_id=item.item_id, question=question, evidence_id=item.evidence_id
            )
            context = self.retriever.build_context(retrieved)
            self._global_retrieval_cache[cache_key] = (retrieved, context)

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

    def _process_task(self, task: tuple[Item, str, str, dict]) -> Generation | None:
        item, language, condition, model_config = task
        model_id = model_config["id"]
        adapter_name = model_config["adapter"]
        params = model_config.get("params", {})
        question = item.question_bn if language == "bn" else item.question_banglish

        # Build prompt + evidence_ids_used (§9.10)
        truncated_input = False
        if condition == "C0":
            evidence_ids_used: list[str] = []
            prompt, template_name = self.prompt_builder.build_prompt(
                item=item, language=language, condition=condition
            )
        elif condition == "C1":
            evidence = self._get_evidence(item)
            evidence_ids_used = [item.evidence_id]
            max_input_tokens = model_config.get("max_input_tokens")
            if max_input_tokens and self.retriever is not None:
                max_ev_tokens = max(50, max_input_tokens - params.get("max_tokens", 512) - 300)
                ev_chunks = self.retriever.get_evidence_chunks(item.evidence_id)
                truncated_ev = self.retriever.build_context(ev_chunks, max_tokens=max_ev_tokens)
                if len(truncated_ev) < len(evidence):
                    evidence = truncated_ev
                    truncated_input = True
            prompt, template_name = self.prompt_builder.build_prompt(
                item=item, language=language, condition=condition, evidence=evidence
            )
        elif condition in ("C2", "C3"):
            if self.retriever is None:
                logger.warning(f"No retriever for {condition}, skipping")
                return None
            retrieved, retrieved_context = self._get_retrieval_for(
                item, language, question
            )
            seen: set[str] = set()
            evidence_ids_used = []
            for p in retrieved:
                if p["evidence_id"] not in seen:
                    seen.add(p["evidence_id"])
                    evidence_ids_used.append(p["evidence_id"])
            max_input_tokens = model_config.get("max_input_tokens")
            if max_input_tokens:
                max_ctx_tokens = max(50, max_input_tokens - params.get("max_tokens", 512) - 300)
                truncated_ctx = self.retriever.build_context(retrieved, max_tokens=max_ctx_tokens)
                if len(truncated_ctx) < len(retrieved_context):
                    retrieved_context = truncated_ctx
                    truncated_input = True
            prompt, template_name = self.prompt_builder.build_prompt(
                item=item, language=language, condition=condition,
                retrieved_context=retrieved_context
            )
        else:
            raise ValueError(f"Unknown condition: {condition}")

        generation_id = self._generate_generation_id(
            item.item_id, language, condition, model_id
        )

        with self._generations_lock:
            if generation_id in self.existing_generations:
                logger.info(f"Generation {generation_id} already in generations.jsonl, skipping")
                return self.existing_generations[generation_id]

        # Check cache
        model_version = self._get_model_version(model_config, adapter_name)
        cache_key = self.cache._make_cache_key(
            prompt=prompt, model_id=model_id, model_version=model_version,
            temperature=params.get("temperature", 0.0),
            max_tokens=params.get("max_tokens", 512),
            seed=params.get("seed", 42)
        )

        cached = self.cache.get(cache_key, self.cache.SCHEMA_VERSION)
        if cached and cached.response:
            logger.info(f"Cache hit for {cache_key[:8]}...")
            gen = self._create_generation_from_cache(
                cached, item, language, condition, model_id, model_version,
                prompt=prompt, evidence_ids_used=evidence_ids_used, truncated_input=truncated_input,
                generation_id=generation_id,
            )
            with self._generations_lock:
                write_jsonl_atomic(str(self.generations_path), gen.model_dump())
                flush_writer(self.generations_path)
                self.existing_generations[generation_id] = gen
            return gen

        lock_path = self.locks_dir / f"{generation_id}.lock"
        try:
            lock_fd = create_lock_atomic(lock_path)
        except LockError:
            logger.info(f"Generation {generation_id} already claimed, skipping")
            return None

        try:
            adapter_cls = get_adapter_class(adapter_name)
            adapter = adapter_cls(model_id=model_id, params=params)
            result = adapter.generate(prompt)

            if result.error:
                logger.error(f"Generation error on item {item.item_id}, model {model_id}: {result.error}")
                raise RuntimeError(f"Generation failed for model {model_id} on item {item.item_id}: {result.error}")

            if not result.text:
                logger.error(f"Empty completion from model {model_id} on item {item.item_id}")
                raise RuntimeError(f"Model {model_id} returned empty completion on item {item.item_id}")

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
                truncated_input=truncated_input,
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

            with self._generations_lock:
                write_jsonl_atomic(str(self.generations_path), generation.model_dump())
                flush_writer(self.generations_path)
                self.existing_generations[generation_id] = generation
                self.generated_count += 1

            return generation
        finally:
            release_lock(lock_fd)
            remove_lock(lock_path)

    def generate_all(self) -> list[Generation]:
        """
        Run generation across all items, languages, conditions, and models.

        Returns:
            List of Generation objects created.
        """
        tasks = []
        for item in self.items:
            for language in self.languages:
                for condition in self.conditions:
                    for model_config in self.models:
                        tasks.append((item, language, condition, model_config))

        generations = []
        if self.workers > 1:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                results = list(executor.map(self._process_task, tasks))
                generations = [g for g in results if g is not None]
        else:
            for task in tasks:
                g = self._process_task(task)
                if g is not None:
                    generations.append(g)

        return generations

    def _get_evidence(self, item: Item) -> str:
        """Get chunk-matched evidence for C1 (§8.10)."""
        if self.retriever is None:
            return ""
        evidence_chunks = self.retriever.get_evidence_chunks(item.evidence_id)
        return self.retriever.build_context(evidence_chunks)

    def _create_generation_from_cache(
        self, cached, item, language, condition, model_id, model_version,
        prompt: str = "", evidence_ids_used: list[str] | None = None, truncated_input: bool = False,
        generation_id: str = "",
    ) -> Generation:
        """Create a Generation object from cached data."""
        return Generation(
            run_id=self.run_id,
            generation_id=generation_id or cached.generation_id,
            item_id=item.item_id,
            language=language,
            condition=condition,
            model_id=model_id,
            model_version=model_version,
            prompt=prompt,
            prompt_hash=hash_prompt(prompt) if prompt else "",
            prompt_tokens=len(prompt.split()) if prompt else 0,
            response=cached.response,
            response_tokens=len(cached.response.split()),
            evidence_ids_used=evidence_ids_used or [],
            temperature=0.0,
            seed=42,
            max_tokens=512,
            timestamp=cached.timestamp,
            latency_ms=None,
            cost_usd=None,
            truncated_input=truncated_input,
        )
