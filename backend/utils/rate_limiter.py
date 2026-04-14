"""
Simple in-memory sliding window rate limiter.
"""
from __future__ import annotations

import time
from collections import deque
from threading import Lock

from config import settings


class RateLimiter:
    """
    Sliding window rate limiter using an in-memory dict keyed by client IP.
    Thread-safe via a per-key lock strategy (single global lock for simplicity).
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, deque[float]] = {}
        self._lock = Lock()

    def is_allowed(self, key: str) -> bool:
        """Return True if the request is within the rate limit, False otherwise."""
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = deque()

            bucket = self._buckets[key]

            # Evict timestamps outside the sliding window
            while bucket and bucket[0] < cutoff:
                bucket.popleft()

            if len(bucket) >= self.max_requests:
                return False

            bucket.append(now)
            return True


# Shared instance used by the benchmark router – values driven by config
benchmark_rate_limiter = RateLimiter(
    max_requests=settings.BENCHMARK_RATE_LIMIT_MAX_REQUESTS,
    window_seconds=settings.BENCHMARK_RATE_LIMIT_WINDOW_SECONDS,
)
