"""Per-category hit counters for the recommendation service.

Added to answer "which catalog category are we recommending most" without a
real metrics backend — a plain in-process counter, incremented on every
`get_recommendations` call.
"""
from __future__ import annotations

import threading

_category_hits: dict[str, int] = {}

# Guards the read-modify-write in record_hit(); without this, two threads can
# read the same "current" value and each write current+1, losing one increment.
_lock = threading.Lock()


def record_hit(category: str) -> None:
    """Increment the hit counter for `category`."""
    with _lock:
        current = _category_hits.get(category, 0)
        _category_hits[category] = current + 1


def hit_count(category: str) -> int:
    return _category_hits.get(category, 0)


def total_hits() -> int:
    return sum(_category_hits.values())
