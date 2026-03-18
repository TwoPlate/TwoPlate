"""
Bayleys Commercial & Industrial scraper.
Bayleys is one of NZ's largest commercial real estate agencies.

Search URL:
  https://www.bayleys.co.nz/commercial-industrial/listings
  Filters: property_type=industrial, for_sale=true

Bayleys uses a REST API that returns JSON — we query it directly.
Endpoint discovered via browser DevTools network tab:
  https://www.bayleys.co.nz/api/listing/search
"""
import json
import asyncio
import re
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, make_id, extract_region
from models import PropertyListing
from analyzer import parse_area, parse_price, parse_yield

# Bayleys search API endpoint (JSON)
API_URL = "https://www.bayleys.co.nz/api/listing/search"

# Fallback HTML search pages
SEARCH_PAGES = [
    "https://www.bayleys.co.nz/commercial-industrial/listings?saleMethod=for-sale&propertyType=industrial-and-business",
    "https://www.bayleys.co.nz/commercial-industrial/listings?saleMethod=for-sale&propertyType=industrial-land",
    "https://www.bayleys.co.nz/commercial-industrial/listings?saleMethod=for-sale&propertyType=warehouse",
]


class BayleyScraper(BaseScraper):
    source_name = "bayleys"
    base_url = "https://www.bayleys.co.nz"

    async def scrape(self, progress_callback=None) -> list[PropertyListing]:
        listings = []
        seen_ids = set()

        # Try JSON API first
        if progress_callback:
            progress_callback("Bayleys: querying listings API…")
        api_listings = await self._scrape_api()
        for listing in api_listings:
            if listing.id not in seen_ids:
                seen_ids.add(listing.id)
                finalised = self.finalise_listing(listing)
                if finalised:
                    listings.append(finalised)

        # If API returned nothing, try HTML pages
        if not listings:
            for i, url in enumerate(SEARCH_PAGES):
                if progress_callback:
                    progress_callback(f"Bayleys: scraping page {i + 1}/{len(SEARCH_PAGES)}…")
                html = await self.fetch(url)
                if html:
                    page_listings = self._parse_html(html)
                    for listing in page_listings:
                        if listing.id not in seen_ids:
                            seen_ids.add(listing.id)
                            finalised = self.finalise_listing(listing)
                            if finalised:
                                listings.append(finalised)
                await asyncio.sleep(1.5)

        if progress_callback:
            progress_callback(f"Bayleys: found {len(listings)} industrial listings")
        return listings

    async def _scrape_api(self) -> list[PropertyListing]:
        """Query Bayleys' internal search API for industrial properties."""
        listings = []
        pages_to_fetch = 3

        for page in range(1, pages_to_fetch + 1):
            params = {
                "saleMethod": "for-sale",
                "propertyTypes": "industrial-and-business,warehouse,industrial-land",
                "page": page,
                "pageSize": 24,
                "country": "nz",
            }
            data = await self.fetch_json(API_URL, params=params)
            if not data:
                break

            # Bayleys API response structure varies; try common patterns
            items = (
                data.get("listings")
                or data.get("results")
                or data.get("data", {}).get("listings")
                or []
            )
            if not items:
                break

            for item in items:
                listing = self._parse_api_item(item)
                if listing:
                    listings.append(listing)

            await asyncio.sleep(1.0)

        return listings

    def _parse_api_item(self, item: dict) -> PropertyListing:
        """Parse a single listing from Bayleys API JSON."""
        try:
            url = self.base_url + (item.get("url") or item.get("urlPath") or "")
            if not url or url == self.base_url:
                return None

            title = item.get("heading") or item.get("title") or ""
            address = item.get("address") or item.get("displayAddress") or title
            region = extract_region(
                address + " " + (item.get("region") or item.get("suburb") or "")
            )

            # Price
            price_raw = (
                item.get("askingPrice")
                or item.get("price")
                or item.get("priceSearchSort")
            )
            price = float(price_raw) if price_raw else None
            price_display = item.get("priceDisplay") or (
                f"${price:,.0f}" if price else "Price on application"
            )

            # Rent / yield
            annual_rent = None
            rent_raw = item.get("annualRent") or item.get("currentRent")
            if rent_raw:
                annual_rent = float(rent_raw)
            yield_pct = None
            yield_raw = item.get("yield") or item.get("netYield")
            if yield_raw:
                yield_pct = float(str(yield_raw).replace("%", "").strip())

            # Areas
            floor_area = parse_area(str(item.get("floorArea") or ""))
            land_area = parse_area(str(item.get("landArea") or ""))

            p = PropertyListing(
                id=make_id(self.source_name, url),
                source=self.source_name,
                title=title,
                address=address,
                region=region,
                url=url,
                price=price,
                price_display=price_display,
                annual_rent=annual_rent,
                yield_pct=yield_pct,
                floor_area=floor_area,
                land_area=land_area,
                property_type=item.get("propertyType") or "Industrial",
                description=item.get("description") or item.get("shortDescription") or "",
                image_url=(item.get("images") or [{}])[0].get("url") if item.get("images") else "",
                agent=item.get("agentName") or "",
            )

            # Check if bare land
            pt_lower = (p.property_type + " " + p.title).lower()
            if any(t in pt_lower for t in ["land", "bare", "vacant"]):
                p.is_bare_land = True

            # Check if leased
            if annual_rent or item.get("tenanted") or "lease" in p.description.lower():
                p.is_leased = True
                p.lease_expiry = item.get("leaseExpiry") or ""

            if yield_pct:
                p.yield_display = f"{yield_pct:.1f}% net yield"

            return p
        except Exception as e:
            print(f"[bayleys] parse error: {e}")
            return None

    def _parse_html(self, html: str) -> list[PropertyListing]:
        """Fallback HTML parser for Bayleys listing cards."""
        listings = []
        soup = BeautifulSoup(html, "lxml")

        cards = (
            soup.find_all("div", class_=re.compile(r"(listing|property|card)", re.I))
            or soup.find_all("article")
        )

        for card in cards[:40]:
            try:
                link = card.find("a", href=re.compile(r"/commercial|/industrial|/property"))
                if not link:
                    continue
                href = link.get("href", "")
                url = href if href.startswith("http") else self.base_url + href
                title = link.get_text(strip=True) or card.get_text(strip=True)[:80]

                # Price
                price_tag = card.find(class_=re.compile(r"price", re.I))
                price_text = price_tag.get_text(strip=True) if price_tag else ""
                price = parse_price(price_text)

                # Yield
                yield_text = ""
                yield_tag = card.find(string=re.compile(r"\d+\.?\d*\s*%"))
                if yield_tag:
                    yield_text = str(yield_tag)
                yield_pct = parse_yield(yield_text)

                # Address / region
                addr_tag = card.find(class_=re.compile(r"(address|suburb|location)", re.I))
                address = addr_tag.get_text(strip=True) if addr_tag else title
                region = extract_region(address)

                p = PropertyListing(
                    id=make_id(self.source_name, url),
                    source=self.source_name,
                    title=title,
                    address=address,
                    region=region,
                    url=url,
                    price=price,
                    price_display=price_text or (f"${price:,.0f}" if price else "POA"),
                    yield_pct=yield_pct,
                    yield_display=f"{yield_pct:.1f}% yield" if yield_pct else "",
                )
                listings.append(p)
            except Exception:
                continue

        return listings
