"""
Cross-run cache for Matibhrom using SQLite with WAL mode.
"""

import sqlite3
from pathlib import Path
from typing import Any

from src.schema_version import SCHEMA_VERSION
from src.hashing import hash_cache_key


class CacheEntry:
    """A single cache entry."""

    def __init__(
        self,
        key: str,
        generation_id: str,
        response: str,
        model_version: str,
        config_hash: str,
        timestamp: str = "",
    ):
        self.key = key
        self.generation_id = generation_id
        self.response = response
        self.model_version = model_version
        self.config_hash = config_hash
        self.timestamp = timestamp

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "generation_id": self.generation_id,
            "response": self.response,
            "model_version": self.model_version,
            "config_hash": self.config_hash,
            "timestamp": self.timestamp,
        }


class GenerationCache:
    """SQLite-backed cache for generation results."""

    SCHEMA_VERSION = SCHEMA_VERSION

    def __init__(self, cache_db_path: str | Path):
        self.cache_path = Path(cache_db_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.cache_path), timeout=30)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self) -> None:
        """Create the cache table if it doesn't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                generation_id TEXT,
                response TEXT,
                model_version TEXT,
                schema_version TEXT,
                config_hash TEXT,
                timestamp TEXT
            )
        """)
        self.conn.commit()

    def get(self, key: str, expected_schema: str | None = None) -> CacheEntry | None:
        """
        Get a cache entry by key.

        Args:
            key: Cache key (hash of prompt + model + params)
            expected_schema: If provided, invalidate if schema doesn't match

        Returns:
            CacheEntry if found and valid, None otherwise
        """
        cursor = self.conn.execute(
            "SELECT key, generation_id, response, model_version, schema_version, config_hash, timestamp FROM cache WHERE key = ?",
            (key,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        # Check schema version
        if expected_schema and row[4] != expected_schema:
            self.invalidate(key)
            return None

        return CacheEntry(
            key=row[0],
            generation_id=row[1],
            response=row[2],
            model_version=row[3],
            config_hash=row[5],
            timestamp=row[6],
        )

    def put(
        self,
        key: str,
        generation_id: str,
        response: str,
        model_version: str,
        config_hash: str,
        timestamp: str = "",
    ) -> None:
        """Store a cache entry."""
        self.conn.execute(
            "INSERT OR REPLACE INTO cache (key, generation_id, response, model_version, schema_version, config_hash, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (key, generation_id, response, model_version, SCHEMA_VERSION, config_hash, timestamp),
        )
        self.conn.commit()

    def invalidate(self, key: str) -> None:
        """Remove a cache entry."""
        self.conn.execute("DELETE FROM cache WHERE key = ?", (key,))
        self.conn.commit()

    def invalidate_model_version(self, model_version: str) -> int:
        """Invalidate all entries for a model version. Returns number removed."""
        cursor = self.conn.execute(
            "DELETE FROM cache WHERE model_version = ?", (model_version,)
        )
        self.conn.commit()
        return cursor.rowcount

    def _make_cache_key(self, prompt: str, model_id: str, model_version: str, temperature: float, max_tokens: int, seed: int) -> str:
        """Create a cache key using the same hash function as the runner."""
        return hash_cache_key(prompt, model_id, model_version, temperature, max_tokens, seed)

    def invalidate_schema(self, expected_schema: str) -> int:
        """Invalidate all entries with mismatched schema version. Returns number removed."""
        cursor = self.conn.execute(
            "DELETE FROM cache WHERE schema_version != ?", (expected_schema,)
        )
        self.conn.commit()
        return cursor.rowcount

    def count(self) -> int:
        """Return total cache entries."""
        cursor = self.conn.execute("SELECT COUNT(*) FROM cache")
        return cursor.fetchone()[0]

    def clear(self) -> None:
        """Clear all cache entries."""
        self.conn.execute("DELETE FROM cache")
        self.conn.commit()

    def close(self) -> None:
        """Close the cache connection."""
        self.conn.close()