"""Regression tests for the recommendation service.

test_memory_is_bounded guards the served-id history: it drives many requests
and asserts the internal tracking structure does NOT grow without bound.
"""
from __future__ import annotations

import recommendation_server as rs


def test_returns_recommendations():
    out = rs.get_recommendations(["PRODUCT-0"], max_results=3)
    assert isinstance(out, list)
    assert len(out) <= 3
    assert "PRODUCT-0" not in out


def test_memory_is_bounded():
    # reset module state if the fix exposed a way to; otherwise just measure growth
    start = rs.seen_count()
    for i in range(5000):
        rs.get_recommendations([f"PRODUCT-{i % 20}"])
    growth = rs.seen_count() - start
    # A bounded implementation must not accumulate one entry per request.
    # Allow a small cap (e.g. deque maxlen) but reject unbounded growth.
    assert growth < 1000, (
        f"memory appears unbounded: tracking structure grew by {growth} "
        f"entries over 5000 requests (expected a bounded cap)"
    )


def test_seen_id_history_is_capped():
    # d0d4e59 regression guard: every request pushed its input ids onto the
    # served-id history forever. A capped cache must stop growing at its cap.
    for i in range(3000):
        rs.get_recommendations([f"SKU-{i}"])
    assert rs.seen_count() <= 128, (
        f"served-id history is not capped: {rs.seen_count()} entries after "
        f"3000 distinct requests (expected a bounded cache of at most 128)"
    )
