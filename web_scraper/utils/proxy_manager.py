"""
Proxy management utility for web scraping.

Handles proxy rotation, validation, and failover to avoid
IP blocking and distribute requests across multiple proxies.
"""

import random
import time
from typing import List, Optional, Dict
from pathlib import Path
from collections import deque
import threading


class ProxyManager:
    """
    Manages proxy rotation and validation.

    Supports multiple proxy formats, automatic rotation,
    and proxy health tracking.
    """

    def __init__(
        self,
        proxies: Optional[List[str]] = None,
        proxy_file: Optional[str] = None,
        rotation_strategy: str = "round_robin",  # round_robin, random, weighted
        validate_proxies: bool = False,
        max_failures: int = 3
    ):
        """
        Initialize proxy manager.

        Args:
            proxies: List of proxy URLs
            proxy_file: Path to file containing proxies (one per line)
            rotation_strategy: Strategy for rotating proxies
            validate_proxies: Whether to validate proxies before use
            max_failures: Maximum failures before marking proxy as dead
        """
        self.proxies: List[Dict] = []
        self.rotation_strategy = rotation_strategy
        self.validate_proxies = validate_proxies
        self.max_failures = max_failures

        # Load proxies
        if proxies:
            self._load_proxies(proxies)
        if proxy_file:
            self._load_from_file(proxy_file)

        if not self.proxies:
            raise ValueError("No proxies provided")

        # Rotation state
        self.current_index = 0
        self.proxy_queue = deque(self.proxies)
        self.lock = threading.Lock()

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0
        }

    def _load_proxies(self, proxy_list: List[str]) -> None:
        """Load proxies from list."""
        for proxy in proxy_list:
            self.proxies.append({
                "url": proxy.strip(),
                "failures": 0,
                "successes": 0,
                "last_used": None,
                "is_alive": True,
                "response_time": None
            })

    def _load_from_file(self, file_path: str) -> None:
        """Load proxies from file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Proxy file not found: {file_path}")

        with open(file_path, 'r') as f:
            proxy_list = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            self._load_proxies(proxy_list)

    def get_proxy(self) -> Optional[Dict[str, str]]:
        """
        Get next proxy based on rotation strategy.

        Returns:
            Dictionary with proxy configuration or None if no proxies available
        """
        with self.lock:
            # Filter out dead proxies
            alive_proxies = [p for p in self.proxies if p["is_alive"]]

            if not alive_proxies:
                # Try to resurrect proxies if all are dead
                for proxy in self.proxies:
                    proxy["is_alive"] = True
                    proxy["failures"] = 0
                alive_proxies = self.proxies

            if self.rotation_strategy == "round_robin":
                proxy = self._round_robin(alive_proxies)
            elif self.rotation_strategy == "random":
                proxy = self._random_selection(alive_proxies)
            elif self.rotation_strategy == "weighted":
                proxy = self._weighted_selection(alive_proxies)
            else:
                proxy = alive_proxies[0]

            proxy["last_used"] = time.time()
            self.stats["total_requests"] += 1

            # Return proxy in requests-compatible format
            return {
                "http": proxy["url"],
                "https": proxy["url"]
            }

    def _round_robin(self, proxies: List[Dict]) -> Dict:
        """Round-robin selection."""
        proxy = proxies[self.current_index % len(proxies)]
        self.current_index += 1
        return proxy

    def _random_selection(self, proxies: List[Dict]) -> Dict:
        """Random selection."""
        return random.choice(proxies)

    def _weighted_selection(self, proxies: List[Dict]) -> Dict:
        """
        Weighted selection based on success rate.

        Proxies with higher success rates are more likely to be selected.
        """
        weights = []
        for proxy in proxies:
            total = proxy["successes"] + proxy["failures"]
            if total == 0:
                weight = 1.0  # New proxy, give it a chance
            else:
                weight = proxy["successes"] / total

            # Boost weight if not used recently
            if proxy["last_used"]:
                time_since_use = time.time() - proxy["last_used"]
                weight *= (1 + min(time_since_use / 60, 1))  # Up to 2x boost

            weights.append(max(weight, 0.1))  # Minimum weight

        return random.choices(proxies, weights=weights, k=1)[0]

    def report_success(self, proxy_url: str) -> None:
        """
        Report successful use of a proxy.

        Args:
            proxy_url: URL of the proxy that was successful
        """
        with self.lock:
            for proxy in self.proxies:
                if proxy["url"] == proxy_url:
                    proxy["successes"] += 1
                    proxy["failures"] = 0  # Reset failure count on success
                    self.stats["successful_requests"] += 1
                    break

    def report_failure(self, proxy_url: str) -> None:
        """
        Report failed use of a proxy.

        Args:
            proxy_url: URL of the proxy that failed
        """
        with self.lock:
            for proxy in self.proxies:
                if proxy["url"] == proxy_url:
                    proxy["failures"] += 1
                    self.stats["failed_requests"] += 1

                    # Mark as dead if too many failures
                    if proxy["failures"] >= self.max_failures:
                        proxy["is_alive"] = False
                    break

    def get_stats(self) -> Dict:
        """
        Get proxy usage statistics.

        Returns:
            Dictionary with statistics
        """
        with self.lock:
            alive_count = sum(1 for p in self.proxies if p["is_alive"])

            return {
                **self.stats,
                "total_proxies": len(self.proxies),
                "alive_proxies": alive_count,
                "dead_proxies": len(self.proxies) - alive_count,
                "proxies": [
                    {
                        "url": p["url"],
                        "successes": p["successes"],
                        "failures": p["failures"],
                        "is_alive": p["is_alive"],
                        "last_used": p["last_used"]
                    }
                    for p in self.proxies
                ]
            }

    def reset_proxy(self, proxy_url: str) -> None:
        """
        Reset a proxy's statistics and mark it as alive.

        Args:
            proxy_url: URL of the proxy to reset
        """
        with self.lock:
            for proxy in self.proxies:
                if proxy["url"] == proxy_url:
                    proxy["failures"] = 0
                    proxy["successes"] = 0
                    proxy["is_alive"] = True
                    break

    def add_proxy(self, proxy_url: str) -> None:
        """
        Add a new proxy to the pool.

        Args:
            proxy_url: URL of the proxy to add
        """
        with self.lock:
            # Check if proxy already exists
            if any(p["url"] == proxy_url for p in self.proxies):
                return

            self.proxies.append({
                "url": proxy_url,
                "failures": 0,
                "successes": 0,
                "last_used": None,
                "is_alive": True,
                "response_time": None
            })

    def remove_proxy(self, proxy_url: str) -> None:
        """
        Remove a proxy from the pool.

        Args:
            proxy_url: URL of the proxy to remove
        """
        with self.lock:
            self.proxies = [p for p in self.proxies if p["url"] != proxy_url]
