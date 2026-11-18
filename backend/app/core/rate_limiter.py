import time
from collections import defaultdict, deque
from typing import Dict, Tuple
from fastapi import HTTPException, Request, status
from app.config import get_settings


class RateLimiter:
    """
    Sliding window rate limiter tracking request frequencies per client.
    Keyed by client IP address or user/session identifier.
    """

    def __init__(self, requests_per_minute: int | None = None):
        settings = get_settings()
        self.limit = requests_per_minute or settings.RATE_LIMIT_PER_MINUTE
        self.window_seconds = 60
        # Stores deques of monotonic timestamps per identifier
        self._history: Dict[str, deque] = defaultdict(deque)

    def _clean_old_requests(self, key: str, current_time: float) -> None:
        """Removes entries older than the current sliding window."""
        window_start = current_time - self.window_seconds
        client_queue = self._history[key]
        while client_queue and client_queue[0] <= window_start:
            client_queue.popleft()

    def check(self, key: str) -> Tuple[bool, int, int]:
        """
        Evaluates if a request from 'key' is permitted.

        Returns:
            Tuple[bool, int, int]: (allowed, remaining_quota, retry_after_seconds)
        """
        now = time.time()
        self._clean_old_requests(key, now)
        client_queue = self._history[key]

        if len(client_queue) >= self.limit:
            # Over quota
            oldest_timestamp = client_queue[0]
            retry_after = int(self.window_seconds - (now - oldest_timestamp)) + 1
            return False, 0, max(1, retry_after)

        # Record this request
        client_queue.append(now)
        remaining = self.limit - len(client_queue)
        return True, remaining, 0

    def enforce(self, request: Request, identifier: str | None = None) -> int:
        """
        FastAPI dependency helper that raises HTTP 429 if the request quota is exceeded.

        Returns:
            int: Remaining requests in current window.
        """
        # Determine client key: header > explicit identifier > client host IP
        key = identifier or request.headers.get("x-user-id") or request.headers.get("x-session-id")
        if not key:
            key = request.client.host if request.client else "anonymous-client"

        allowed, remaining, retry_after = self.check(key)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: maximum {self.limit} requests per minute allowed.",
                headers={"Retry-After": str(retry_after), "X-RateLimit-Remaining": "0"}
            )
        return remaining

    def reset(self) -> None:
        """Clears all tracking history."""
        self._history.clear()


# Global singleton instance
rate_limiter = RateLimiter()
