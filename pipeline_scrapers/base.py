"""
Base class for all Kernohan Engineering sales pipeline scrapers.
"""
from __future__ import annotations
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Callable, Optional

import httpx
from bs4 import BeautifulSoup

from pipeline_models import Opportunity

logger = logging.getLogger(__name__)

# Shared browser-like headers to reduce 403 blocks
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-NZ,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "DNT": "1",
}


class BaseScraper(ABC):
    """Abstract base for all pipeline scrapers."""

    source_name: str = "base"
    display_name: str = "Base"
    base_url: str = ""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=HEADERS,
                follow_redirects=True,
                timeout=httpx.Timeout(30.0),
                verify=False,           # some NZ govt sites have cert issues
            )
        return self._client

    async def _fetch(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch URL and return BeautifulSoup, or None on failure."""
        client = await self._get_client()
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except Exception as exc:
            logger.warning("[%s] Fetch failed for %s: %s", self.source_name, url, exc)
            return None

    async def _fetch_playwright(self, url: str) -> Optional[BeautifulSoup]:
        """Use Playwright headless browser for JS-rendered pages."""
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.set_extra_http_headers(HEADERS)
                await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                await asyncio.sleep(2)
                html = await page.content()
                await browser.close()
            return BeautifulSoup(html, "lxml")
        except Exception as exc:
            logger.warning("[%s] Playwright failed for %s: %s", self.source_name, url, exc)
            return None

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @abstractmethod
    async def scrape(
        self,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> list[Opportunity]:
        """Scrape and return a list of Opportunity objects."""
        ...

    def _cb(self, callback: Optional[Callable], msg: str) -> None:
        if callback:
            callback(msg)
        logger.info("[%s] %s", self.source_name, msg)
