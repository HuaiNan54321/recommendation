"""Per-category hit counters for the recommendation service.

Added to answer "which catalog category are we recommending most" without a
real metrics backend — a plain in-process counter, incremented on every
`get_recommendations` call.

`record_hit()` is called concurrently from the gRPC thread pool, so every
access to the shared dict goes through `_lock` to keep the read-modify-write
atomic (an unsynchronized get-then-set loses increments under contention).
"""
from __future__ import annotations

import threading

_category_hits: dict[str, int] = {}
_lock = threading.Lock()


def record_hit(category: str) -> None:
    """Increment the hit counter for `category` (thread-safe)."""
    with _lock:
        _category_hits[category] = _category_hits.get(category, 0) + 1


def hit_count(category: str) -> int:
    with _lock:
        return _category_hits.get(category, 0)


def total_hits() -> int:
    with _lock:
        return sum(_category_hits.values())
