"""
Base scraper class with shared utilities.
All scrapers inherit from this.
"""
import asyncio
import re
import hashlib
from abc import ABC, abstractmethod
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from models import PropertyListing
from analyzer import (
    score_development_potential,
    parse_area,
    parse_price,
    parse_yield,
)

# Shared headers that mimic a real browser
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-NZ,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

NZ_REGIONS = [
    "Auckland", "Wellington", "Canterbury", "Waikato", "Bay of Plenty",
    "Manawatu-Whanganui", "Otago", "Hawke's Bay", "Taranaki", "Northland",
    "Marlborough", "Nelson", "West Coast", "Gisborne", "Southland",
    "Hamilton", "Tauranga", "Christchurch", "Dunedin", "Napier",
    "New Plymouth", "Palmerston North", "Invercargill", "Rotorua",
]

INDUSTRIAL_TERMS = [
    "industrial", "warehouse", "factory", "workshop", "depot",
    "distribution", "logistics", "manufacturing", "storage", "shed",
    "stud", "hardstand", "yard", "trade",
]


def make_id(source: str, url: str) -> str:
    """Create a stable unique ID from source + URL."""
    return hashlib.md5(f"{source}:{url}".encode()).hexdigest()[:16]


def extract_region(text: str) -> str:
    """Try to identify which NZ region a property is in."""
    text_lower = text.lower()
    for region in NZ_REGIONS:
        if region.lower() in text_lower:
            return region
    return "New Zealand"


def is_industrial(title: str, description: str, property_type: str = "") -> bool:
    """
    Return True if the listing appears to be industrial/warehouse.
    Filters out retail, residential, office-only, etc.
    """
    combined = (title + " " + description + " " + property_type).lower()

    # Explicit non-industrial types to reject
    reject_terms = [
        "retail", "shop ", "shopping", "residential", "apartment",
        "house", "home", "unit for sale", "townhouse", "section",
        "lifestyle block", "farm", "office only", "medical",
        "hotel", "motel", "restaurant", "cafe", "childcare",
    ]
    for term in reject_terms:
        if term in combined:
            return False

    # Must match at least one industrial term
    for term in INDUSTRIAL_TERMS:
        if term in combined:
            return True

    # If it says "commercial" but has no industrial terms, skip it
    return False


class BaseScraper(ABC):
    source_name: str = "unknown"
    base_url: str = ""

    def __init__(self):
        self.client = None

    async def fetch(self, url: str, timeout: int = 30) -> Optional[str]:
        """Fetch a URL and return HTML text, or None on failure."""
        try:
            async with httpx.AsyncClient(
                headers=HEADERS,
                follow_redirects=True,
                timeout=timeout,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            print(f"[{self.source_name}] Fetch error for {url}: {e}")
            return None

    async def fetch_json(self, url: str, params: dict = None) -> Optional[dict]:
        """Fetch a URL and return parsed JSON, or None on failure."""
        try:
            async with httpx.AsyncClient(
                headers={**HEADERS, "Accept": "application/json"},
                follow_redirects=True,
                timeout=30,
            ) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"[{self.source_name}] JSON fetch error for {url}: {e}")
            return None

    def finalise_listing(self, listing: PropertyListing) -> Optional[PropertyListing]:
        """
        Post-process a listing: calculate yield, site coverage, dev score.
        Returns None if the listing should be rejected (e.g. not industrial).
        """
        # Filter out non-industrial properties
        if not is_industrial(listing.title, listing.description, listing.property_type):
            return None

        # Calculate derived fields
        listing.calculate_yield()
        listing.calculate_site_coverage()

        # Score development potential
        listing.dev_score, listing.dev_notes = score_development_potential(listing)

        return listing

    @abstractmethod
    async def scrape(self, progress_callback=None) -> list[PropertyListing]:
        """Scrape and return a list of PropertyListing objects."""
        pass
