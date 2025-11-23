"""
Rate limiting utility for web scraping.

Implements token bucket algorithm for rate limiting requests
with configurable delays and politeness settings.
"""

import time
import threading
from typing import Optional
from collections import deque


class RateLimiter:
    """
    Rate limiter using token bucket algorithm.

    Ensures requests are made at a controlled rate to respect
    server resources and avoid being blocked.
    """

    def __init__(
        self,
        requests_per_second: float = 1.0,
        burst_size: Optional[int] = None,
        delay_between_requests: float = 0.0
    ):
        """
        Initialize the rate limiter.

        Args:
            requests_per_second: Maximum requests per second
            burst_size: Maximum burst size (default: requests_per_second * 2)
            delay_between_requests: Additional delay between requests in seconds
        """
        self.rate = requests_per_second
        self.delay = delay_between_requests
        self.burst_size = burst_size or int(requests_per_second * 2)

        # Token bucket implementation
        self.tokens = self.burst_size
        self.last_update = time.time()
        self.lock = threading.Lock()

        # Request history for statistics
        self.request_times = deque(maxlen=1000)

    def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens before making a request.

        This method blocks until enough tokens are available.

        Args:
            tokens: Number of tokens to acquire
        """
        with self.lock:
            while self.tokens < tokens:
                # Calculate time needed to accumulate tokens
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.rate
                time.sleep(wait_time)
                self._add_tokens()

            self.tokens -= tokens
            self.request_times.append(time.time())

            # Additional politeness delay
            if self.delay > 0:
                time.sleep(self.delay)

    def _add_tokens(self) -> None:
        """Add tokens based on time elapsed since last update."""
        now = time.time()
        elapsed = now - self.last_update
        new_tokens = elapsed * self.rate

        self.tokens = min(self.tokens + new_tokens, self.burst_size)
        self.last_update = now

    def get_stats(self) -> dict:
        """
        Get rate limiter statistics.

        Returns:
            Dictionary with request statistics
        """
        with self.lock:
            if len(self.request_times) < 2:
                return {
                    "total_requests": len(self.request_times),
                    "average_rate": 0.0,
                    "current_tokens": self.tokens
                }

            time_span = self.request_times[-1] - self.request_times[0]
            avg_rate = len(self.request_times) / time_span if time_span > 0 else 0

            return {
                "total_requests": len(self.request_times),
                "average_rate": avg_rate,
                "current_tokens": self.tokens,
                "configured_rate": self.rate
            }

    def reset(self) -> None:
        """Reset the rate limiter to initial state."""
        with self.lock:
            self.tokens = self.burst_size
            self.last_update = time.time()
            self.request_times.clear()


class AdaptiveRateLimiter(RateLimiter):
    """
    Adaptive rate limiter that adjusts based on server responses.

    Automatically slows down if rate limiting errors are detected
    and speeds up if requests are successful.
    """

    def __init__(
        self,
        initial_rate: float = 1.0,
        min_rate: float = 0.1,
        max_rate: float = 10.0,
        **kwargs
    ):
        """
        Initialize adaptive rate limiter.

        Args:
            initial_rate: Starting requests per second
            min_rate: Minimum allowed rate
            max_rate: Maximum allowed rate
            **kwargs: Additional arguments for RateLimiter
        """
        super().__init__(requests_per_second=initial_rate, **kwargs)
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.initial_rate = initial_rate

        self.success_count = 0
        self.failure_count = 0

    def report_success(self) -> None:
        """Report a successful request to potentially increase rate."""
        with self.lock:
            self.success_count += 1

            # Increase rate after consecutive successes
            if self.success_count >= 10:
                self.rate = min(self.rate * 1.1, self.max_rate)
                self.success_count = 0
                self.failure_count = 0

    def report_failure(self) -> None:
        """Report a failed request (rate limiting) to decrease rate."""
        with self.lock:
            self.failure_count += 1

            # Decrease rate immediately on failure
            self.rate = max(self.rate * 0.5, self.min_rate)
            self.success_count = 0
            self.failure_count = 0

    def report_rate_limit_error(self) -> None:
        """Report a rate limit error and apply backoff."""
        with self.lock:
            # Aggressive backoff for rate limit errors
            self.rate = max(self.rate * 0.3, self.min_rate)
            self.success_count = 0

            # Add immediate delay
            time.sleep(5)  # Wait 5 seconds before continuing
