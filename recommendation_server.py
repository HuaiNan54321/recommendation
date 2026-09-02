"""Minimal recommendation service (stand-in for the OTel demo's Python service).

Bugfix revision: restores the bounded recent-id cache that was removed in commit
f18f452. Two things matter here:

1. **It is a real, runnable service.** `python recommendation_server.py` starts an
   HTTP server on :8080 AND a background load thread that keeps calling
   `get_recommendations`.

2. **The bounded cache keeps memory capped.** `get_recommendations` records recent
   ids in a `collections.deque(maxlen=128)` so the working set does not grow
   without limit under sustained load. `test_memory_is_bounded` is the build+test
   gate 代码修复 Agent must turn green before opening a PR.

Kept dependency-light (stdlib only, no gRPC/framework) so 代码修复 Agent can build+test it
with just the stdlib + pytest in the clone, and so the container image stays tiny.
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# --- Bounded recent-id cache: fixed from unbounded list (f18f452) ---
# Keep only the most recent ids so the working set stays capped under
# sustained load; prevents the OOM regression introduced in f18f452.
_seen_product_ids: deque[str] = deque(maxlen=128)

CATALOG = [f"PRODUCT-{i}" for i in range(20)]

# request counter, exposed via /metrics so the climb is observable externally too
_request_count = 0


def get_recommendations(input_product_ids: list[str], max_results: int = 5) -> list[str]:
    """Return up to max_results recommended product ids not already in the input."""
    global _request_count
    _request_count += 1
    # bounded: record recent ids only, capped to maxlen
    _seen_product_ids.extend(input_product_ids)

    candidates = [p for p in CATALOG if p not in set(input_product_ids)]
    return candidates[:max_results]


def seen_count() -> int:
    """Exposed for the regression test to assert memory is bounded."""
    return len(_seen_product_ids)


# --------------------------------------------------------------------------
# Runnable service: HTTP endpoints + a self-driving background load thread.
# This is what makes the leak a LIVE, observable runtime fault rather than a
# static code smell. Imported as a module (by pytest) none of this runs.
# --------------------------------------------------------------------------

class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (stdlib API)
        if self.path.startswith("/recommend"):
            out = get_recommendations(["PRODUCT-0", "PRODUCT-1"])
            self._json({"recommendations": out})
        elif self.path.startswith("/metrics"):
            # Prometheus text-exposition: the two signals 故障诊断处置 Agent can scrape.
            body = (
                "# HELP recommendation_seen_ids_total tracked product ids (unbounded leak)\n"
                "# TYPE recommendation_seen_ids_total gauge\n"
                f"recommendation_seen_ids_total {seen_count()}\n"
                "# HELP recommendation_requests_total requests served\n"
                "# TYPE recommendation_requests_total counter\n"
                f"recommendation_requests_total {_request_count}\n"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(body.encode())
        elif self.path.startswith("/healthz"):
            self._json({"status": "ok"})
        else:
            self._json({"service": "recommendation", "seen": seen_count()})

    def _json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):  # silence per-request logging
        pass


def _background_load(rps: float) -> None:
    """Continuously exercise the service so memory climbs on its own (no external
    load generator needed). Each tick grows _seen_product_ids -> monotonic RSS rise.

    The synthetic session ids carry a payload so the leak is visible as real RSS
    growth in `docker stats` within a couple of minutes, not just an item count."""
    i = 0
    interval = 1.0 / rps if rps > 0 else 0.01
    pad = "x" * 256  # make each leaked entry weigh enough to move RSS
    while True:
        # batch several ids per tick to make the climb clearly visible in minutes
        get_recommendations([f"PRODUCT-{i % 20}", f"SKU-{i}", f"SESSION-{i}-{pad}"])
        i += 1
        time.sleep(interval)


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    rps = float(os.environ.get("LOAD_RPS", "200"))
    if rps > 0:
        t = threading.Thread(target=_background_load, args=(rps,), daemon=True)
        t.start()
        print(f"[recommendation] background load started ~{rps} rps", flush=True)
    srv = ThreadingHTTPServer(("0.0.0.0", port), _Handler)
    print(f"[recommendation] serving on :{port} (bounded cache revision)", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
