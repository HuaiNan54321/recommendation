"""Per-category hit counters for the recommendation service.

Added to answer "which catalog category are we recommending most" without a
real metrics backend — a plain in-process counter, incremented on every
`get_recommendations` call and exposed via `/metrics`.
"""
from __future__ import annotations

import threading

_category_hits: dict[str, int] = {}
_lock = threading.Lock()


def record_hit(category: str) -> None:
    """Increment the hit counter for `category`.

    The read-modify-write on the shared dict is serialized with a lock so
    that concurrent request threads cannot both read the same current value
    and lose one of the increments.
    """
    with _lock:
        _category_hits[category] = _category_hits.get(category, 0) + 1


def hit_count(category: str) -> int:
    return _category_hits.get(category, 0)


def total_hits() -> int:
    return sum(_category_hits.values())
