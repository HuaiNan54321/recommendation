"""Per-category hit counters for the recommendation service.

Added to answer "which catalog category are we recommending most" without a
real metrics backend — a plain in-process counter, incremented on every
`get_recommendations` call.
"""
from __future__ import annotations

import threading

_category_hits: dict[str, int] = {}

# record_hit() is called concurrently: the server is a ThreadingHTTPServer (one
# thread per request) and the background load thread exercises it too. The GIL
# makes single dict ops atomic but not the read-modify-write below, so guard the
# whole increment — otherwise interleaved threads read the same old value and
# increments get lost.
_lock = threading.Lock()


def record_hit(category: str) -> None:
    """Increment the hit counter for `category`."""
    with _lock:
        _category_hits[category] = _category_hits.get(category, 0) + 1


def hit_count(category: str) -> int:
    return _category_hits.get(category, 0)


def total_hits() -> int:
    return sum(_category_hits.values())
