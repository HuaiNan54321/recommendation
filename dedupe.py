"""Dedupe helper for recommendation candidate ids.

Added so a single response never lists the same product twice, even if the
scoring step produced overlapping candidates from multiple sources (catalog +
personalized model).
"""
from __future__ import annotations


def dedupe_ids(product_ids: list[str]) -> list[str]:
    """Return product_ids with exact duplicates removed, preserving order."""
    seen: set[str] = set()
    out: list[str] = []
    for pid in product_ids:
        # Normalize the key once and use it for both the membership check and
        # the store, so "PRODUCT-1" and "product-1" collapse to one entry.
        key = pid.lower()
        if key not in seen:
            seen.add(key)
            out.append(pid)
    return out
