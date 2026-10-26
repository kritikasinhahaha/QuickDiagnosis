"""
QuickDiagnosis - Medical Data Cache Service
Provides thread-safe, disk-persisted caching with TTL expiration
and graceful offline/stale fallback for external medical services.
"""

import json
import os
import time
import threading
from typing import Any, Dict, Optional


class MedicalDataCache:
    """
    Thread-safe disk-backed cache for NIH MedlinePlus and FDA responses.
    Prevents repeated network queries and supports offline operation.
    """
    DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days

    def __init__(self, cache_file_path: str, default_ttl: int = DEFAULT_TTL_SECONDS):
        self.cache_file = cache_file_path
        self.default_ttl = default_ttl
        self.lock = threading.Lock()
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Loads cached data from JSON file if present."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._memory_cache = data
            except Exception as e:
                # Corrupt cache file recovered gracefully
                self._memory_cache = {}

    def _save_to_disk(self) -> None:
        """Persists current cache dictionary to JSON file."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.cache_file)), exist_ok=True)
            temp_file = self.cache_file + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self._memory_cache, f, indent=2, ensure_ascii=False)
            if os.path.exists(temp_file):
                os.replace(temp_file, self.cache_file)
        except Exception:
            # Non-blocking disk save failure
            pass

    def get(self, key: str, allow_stale: bool = False) -> Optional[Dict[str, Any]]:
        """
        Retrieves a cached item by key.
        Returns None if not found or if expired (unless allow_stale=True).
        """
        with self.lock:
            entry = self._memory_cache.get(key)
            if not entry:
                return None

            timestamp = entry.get("timestamp", 0)
            ttl = entry.get("ttl", self.default_ttl)
            is_expired = (time.time() - timestamp) > ttl

            if is_expired and not allow_stale:
                return None

            result = dict(entry)
            result["is_stale"] = is_expired
            return result

    def set(
        self,
        key: str,
        data: Any,
        ttl: Optional[int] = None,
        source_name: Optional[str] = None,
        source_url: Optional[str] = None
    ) -> None:
        """
        Stores data under key with timestamp and metadata.
        """
        with self.lock:
            self._memory_cache[key] = {
                "data": data,
                "timestamp": time.time(),
                "ttl": ttl if ttl is not None else self.default_ttl,
                "source_name": source_name,
                "source_url": source_url
            }
            self._save_to_disk()

    def has(self, key: str) -> bool:
        """Checks if a valid, unexpired entry exists."""
        return self.get(key, allow_stale=False) is not None

    def clear(self) -> None:
        """Clears all cached records."""
        with self.lock:
            self._memory_cache = {}
            self._save_to_disk()
