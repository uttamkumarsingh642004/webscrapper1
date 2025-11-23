"""
User-Agent rotation utility for web scraping.

Provides realistic user-agent strings and rotation to avoid detection.
"""

import random
from typing import List, Optional
from fake_useragent import UserAgent


class UserAgentRotator:
    """
    Manages user-agent rotation for requests.

    Uses fake-useragent library for realistic user-agents
    and supports custom user-agent lists.
    """

    def __init__(
        self,
        custom_user_agents: Optional[List[str]] = None,
        fallback_user_agent: Optional[str] = None,
        use_fake_ua: bool = True
    ):
        """
        Initialize user-agent rotator.

        Args:
            custom_user_agents: List of custom user-agent strings
            fallback_user_agent: Fallback user-agent if others fail
            use_fake_ua: Whether to use fake-useragent library
        """
        self.custom_user_agents = custom_user_agents or []
        self.use_fake_ua = use_fake_ua

        # Initialize fake-useragent
        self.ua = None
        if use_fake_ua:
            try:
                self.ua = UserAgent()
            except Exception:
                # Fallback if fake-useragent fails
                self.use_fake_ua = False

        # Default fallback user-agent (Chrome on Windows)
        self.fallback_user_agent = fallback_user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        # Common realistic user-agents as backup
        self.default_user_agents = [
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Chrome on Mac
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Firefox on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            # Firefox on Mac
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
            # Safari on Mac
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            # Edge on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            # Chrome on Linux
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]

        # Usage statistics
        self.stats = {
            "total_requests": 0,
            "user_agents_used": {}
        }

    def get_random_user_agent(self) -> str:
        """
        Get a random user-agent string.

        Returns:
            User-agent string
        """
        # Priority: custom > fake-useragent > defaults > fallback
        try:
            if self.custom_user_agents:
                ua = random.choice(self.custom_user_agents)
            elif self.use_fake_ua and self.ua:
                # Get random user-agent from fake-useragent
                ua = self.ua.random
            else:
                ua = random.choice(self.default_user_agents)

            # Update statistics
            self.stats["total_requests"] += 1
            self.stats["user_agents_used"][ua] = self.stats["user_agents_used"].get(ua, 0) + 1

            return ua

        except Exception:
            return self.fallback_user_agent

    def get_chrome(self) -> str:
        """Get Chrome user-agent."""
        try:
            if self.use_fake_ua and self.ua:
                return self.ua.chrome
            else:
                chrome_uas = [ua for ua in self.default_user_agents if "Chrome" in ua and "Edg" not in ua]
                return random.choice(chrome_uas)
        except Exception:
            return self.fallback_user_agent

    def get_firefox(self) -> str:
        """Get Firefox user-agent."""
        try:
            if self.use_fake_ua and self.ua:
                return self.ua.firefox
            else:
                firefox_uas = [ua for ua in self.default_user_agents if "Firefox" in ua]
                return random.choice(firefox_uas)
        except Exception:
            return self.fallback_user_agent

    def get_safari(self) -> str:
        """Get Safari user-agent."""
        try:
            if self.use_fake_ua and self.ua:
                return self.ua.safari
            else:
                safari_uas = [ua for ua in self.default_user_agents if "Safari" in ua and "Chrome" not in ua]
                return random.choice(safari_uas) if safari_uas else self.fallback_user_agent
        except Exception:
            return self.fallback_user_agent

    def get_edge(self) -> str:
        """Get Edge user-agent."""
        try:
            edge_uas = [ua for ua in self.default_user_agents if "Edg" in ua]
            return random.choice(edge_uas) if edge_uas else self.fallback_user_agent
        except Exception:
            return self.fallback_user_agent

    def get_mobile_user_agent(self, platform: str = "random") -> str:
        """
        Get mobile user-agent.

        Args:
            platform: Mobile platform (ios, android, random)

        Returns:
            Mobile user-agent string
        """
        ios_agents = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        ]

        android_agents = [
            "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
        ]

        if platform == "ios":
            return random.choice(ios_agents)
        elif platform == "android":
            return random.choice(android_agents)
        else:
            return random.choice(ios_agents + android_agents)

    def add_custom_user_agent(self, user_agent: str) -> None:
        """
        Add a custom user-agent to the pool.

        Args:
            user_agent: User-agent string to add
        """
        if user_agent not in self.custom_user_agents:
            self.custom_user_agents.append(user_agent)

    def get_stats(self) -> dict:
        """
        Get usage statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            **self.stats,
            "total_custom_user_agents": len(self.custom_user_agents),
            "using_fake_ua": self.use_fake_ua
        }

    def reset_stats(self) -> None:
        """Reset usage statistics."""
        self.stats = {
            "total_requests": 0,
            "user_agents_used": {}
        }
