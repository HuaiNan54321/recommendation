"""Per-category hit counters for the recommendation service.

Added to answer "which catalog category are we recommending most" without a
real metrics backend — a plain in-process counter, incremented on every
`get_recommendations` call.

The server handles requests on multiple threads (ThreadingHTTPServer), so all
access to the shared counter dict is serialized with a module-level lock.
"""
from __future__ import annotations

import threading

_category_hits: dict[str, int] = {}
_lock = threading.Lock()


def record_hit(category: str) -> None:
    """Increment the hit counter for `category` (thread-safe)."""
    with _lock:
        current = _category_hits.get(category, 0)
        _category_hits[category] = current + 1


def hit_count(category: str) -> int:
    with _lock:
        return _category_hits.get(category, 0)


def total_hits() -> int:
    with _lock:
        return sum(_category_hits.values())
