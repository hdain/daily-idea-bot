"""Data scraper module for collecting tech trends from various sources.

Extensible architecture - add new sources by:
1. Create a new class inheriting from BaseScraper
2. Register it in AVAILABLE_SCRAPERS
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx


@dataclass
class TrendItem:
    """Represents a trending item from any source."""

    source: str
    title: str
    url: str
    score: int | None = None
    description: str | None = None


class BaseScraper(ABC):
    """Base class for all trend scrapers. Extend this to add new sources."""

    name: str = "base"
    requires_sela: bool = False

    def __init__(self, client: httpx.AsyncClient, sela_api_key: str | None = None):
        self.client = client
        self.sela_api_key = sela_api_key

    @abstractmethod
    async def fetch(self) -> list[TrendItem]:
        """Fetch trends from this source. Must be implemented by subclasses."""
        pass

    async def _sela_scrape(
        self,
        url: str,
        scrape_type: str,
        post_count: int = 10,
        timeout_ms: int = 60000,
    ) -> dict:
        """Helper method for Sela Net API calls."""
        if not self.sela_api_key:
            return {}

        resp = await self.client.post(
            "https://api.selanetwork.io/api/rpc/scrapeUrl",
            headers={"Authorization": f"Bearer {self.sela_api_key}"},
            json={
                "url": url,
                "scrapeType": scrape_type,
                "timeoutMs": timeout_ms,
                "postCount": post_count,
                "scrollPauseTime": 2000,
            },
            timeout=90.0,
        )
        if resp.status_code != 200:
            print(f"[Sela API] {resp.status_code}: {resp.text}")
        return resp.json()


# =============================================================================
# Twitter Scraper (requires Sela Net)
# =============================================================================
class TwitterScraper(BaseScraper):
    """Scrape trending dev content from Twitter/X using Sela Net."""

    name = "Twitter/X"
    requires_sela = True

    DEFAULT_QUERIES = [
        "AI agent",
        "developer tools",
        "tech meme",
        "viral app",
    ]

    def __init__(
        self,
        client: httpx.AsyncClient,
        sela_api_key: str | None = None,
        search_queries: list[str] | None = None,
        post_count: int = 5,
    ):
        super().__init__(client, sela_api_key)
        # Load from env if not provided
        if search_queries is None:
            import os
            env_queries = os.getenv("TWITTER_QUERIES", "")
            if env_queries:
                search_queries = [q.strip() for q in env_queries.split(",") if q.strip()]
        self.search_queries = search_queries or self.DEFAULT_QUERIES
        self.post_count = post_count

    async def fetch(self) -> list[TrendItem]:
        if not self.sela_api_key:
            return []

        from urllib.parse import quote

        all_items: list[TrendItem] = []

        for query in self.search_queries:
            try:
                search_url = f"https://x.com/search?q={quote(query)}&f=top"

                data = await self._sela_scrape(
                    url=search_url,
                    scrape_type="TWITTER_PROFILE",
                    post_count=self.post_count,
                )

                posts = data.get("data", {}).get("result", [])
                for item in posts[:self.post_count]:
                    tweet_url = item.get("tweetUrl", "")
                    if tweet_url and not tweet_url.startswith("http"):
                        tweet_url = f"https://x.com{tweet_url}"
                    all_items.append(
                        TrendItem(
                            source=f"{self.name} ({query})",
                            title=item.get("content", "")[:100],
                            url=tweet_url,
                            score=item.get("likesCount") or item.get("viewsCount"),
                            description=item.get("content"),
                        )
                    )
            except Exception as e:
                print(f"[{self.name}] Error searching '{query}': {e}")

        return all_items


# =============================================================================
# GitHub Scraper (free API, no Sela required)
# =============================================================================
class GitHubScraper(BaseScraper):
    """Scrape trending repositories from GitHub (free API, no Sela needed)."""

    name = "GitHub"
    requires_sela = False

    async def fetch(self) -> list[TrendItem]:
        try:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            resp = await self.client.get(
                "https://api.github.com/search/repositories",
                params={
                    "q": f"created:>{yesterday}",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 10,
                },
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            data = resp.json()

            return [
                TrendItem(
                    source=self.name,
                    title=f"{repo['full_name']} - {repo['language'] or 'Unknown'}",
                    url=repo["html_url"],
                    score=repo["stargazers_count"],
                    description=repo.get("description"),
                )
                for repo in data.get("items", [])[:10]
            ]
        except Exception as e:
            print(f"[{self.name}] Error: {e}")
            return []


# =============================================================================
# Available Scrapers Registry
# =============================================================================
AVAILABLE_SCRAPERS: dict[str, type[BaseScraper]] = {
    "twitter": TwitterScraper,
    "github": GitHubScraper,
}

DEFAULT_SCRAPERS = ["twitter", "github"]


# =============================================================================
# Main Scraper Orchestrator
# =============================================================================
class TrendScraper:
    """Orchestrates multiple trend scrapers.

    Usage:
        scraper = TrendScraper(sela_api_key="...")
        trends = await scraper.get_all_trends()
    """

    def __init__(
        self,
        sela_api_key: str | None = None,
        enabled_scrapers: list[str] | None = None,
        scraper_configs: dict[str, dict] | None = None,
    ):
        self.sela_api_key = sela_api_key
        self.enabled_scrapers = enabled_scrapers or DEFAULT_SCRAPERS
        self.scraper_configs = scraper_configs or {}
        self.client = httpx.AsyncClient(timeout=30.0)
        self._scrapers: list[BaseScraper] = []
        self._init_scrapers()

    def _init_scrapers(self) -> None:
        """Initialize enabled scrapers."""
        for name in self.enabled_scrapers:
            if name not in AVAILABLE_SCRAPERS:
                print(f"Warning: Unknown scraper '{name}', skipping")
                continue

            scraper_class = AVAILABLE_SCRAPERS[name]

            # Skip Sela-dependent scrapers if no API key
            if scraper_class.requires_sela and not self.sela_api_key:
                print(f"Warning: '{name}' requires Sela API key, skipping")
                continue

            config = self.scraper_configs.get(name, {})

            scraper = scraper_class(
                client=self.client,
                sela_api_key=self.sela_api_key,
                **config,
            )
            self._scrapers.append(scraper)

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()

    async def get_all_trends(self) -> list[TrendItem]:
        """Fetch trends from all enabled scrapers concurrently."""
        if not self._scrapers:
            print("Warning: No scrapers enabled")
            return []

        tasks = [scraper.fetch() for scraper in self._scrapers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_trends: list[TrendItem] = []
        for i, result in enumerate(results):
            if isinstance(result, list):
                all_trends.extend(result)
            elif isinstance(result, Exception):
                print(f"Error in {self._scrapers[i].name}: {result}")

        return all_trends

    def list_available_scrapers(self) -> list[str]:
        """List all available scraper names."""
        return list(AVAILABLE_SCRAPERS.keys())

    def list_enabled_scrapers(self) -> list[str]:
        """List currently enabled scraper names."""
        return [s.name for s in self._scrapers]
