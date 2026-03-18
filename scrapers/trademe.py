"""
Trade Me Property scraper — NZ's largest marketplace.
Scrapes industrial/commercial/warehouse listings for sale.

Trade Me URL pattern for commercial property:
  https://www.trademe.co.nz/a/property/commercial/for-sale
  Filter by type: ?property_type=Industrial, Warehouse, etc.

Trade Me renders via React (Next.js), so we look for __NEXT_DATA__ JSON
embedded in the HTML which contains the listing data before hydration.
"""
import json
import re
import asyncio
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, make_id, extract_region, INDUSTRIAL_TERMS
from models import PropertyListing
from analyzer import parse_area, parse_price, parse_yield

SEARCH_URLS = [
    "https://www.trademe.co.nz/a/property/commercial/for-sale?property_type=Industrial&rows=50",
    "https://www.trademe.co.nz/a/property/commercial/for-sale?property_type=Warehouse&rows=50",
    "https://www.trademe.co.nz/a/property/commercial/for-sale?property_type=Industrial+Land&rows=50",
    "https://www.trademe.co.nz/a/property/commercial/for-sale?property_type=Factory&rows=50",
]


class TrademeScraper(BaseScraper):
    source_name = "trademe"
    base_url = "https://www.trademe.co.nz"

    async def scrape(self, progress_callback=None) -> list[PropertyListing]:
        listings = []
        seen_ids = set()

        for i, url in enumerate(SEARCH_URLS):
            if progress_callback:
                progress_callback(f"Trade Me: fetching page {i + 1}/{len(SEARCH_URLS)}…")
            html = await self.fetch(url)
            if not html:
                continue
            page_listings = self._parse_page(html, url)
            for listing in page_listings:
                if listing.id not in seen_ids:
                    seen_ids.add(listing.id)
                    finalised = self.finalise_listing(listing)
                    if finalised:
                        listings.append(finalised)
            await asyncio.sleep(1.5)  # polite delay

        if progress_callback:
            progress_callback(f"Trade Me: found {len(listings)} industrial listings")
        return listings

    def _parse_page(self, html: str, source_url: str) -> list[PropertyListing]:
        """
        Trade Me injects data as __NEXT_DATA__ JSON in a script tag.
        We extract that JSON and parse listing cards from it.
        If that fails we fall back to HTML card parsing.
        """
        listings = []

        # --- Try __NEXT_DATA__ extraction ---
        try:
            soup = BeautifulSoup(html, "lxml")
            next_data_tag = soup.find("script", {"id": "__NEXT_DATA__"})
            if next_data_tag:
                data = json.loads(next_data_tag.string)
                cards = self._extract_from_next_data(data)
                if cards:
                    return cards
        except Exception as e:
            print(f"[trademe] __NEXT_DATA__ parse failed: {e}")

        # --- Fallback: scrape HTML listing cards ---
        try:
            soup = BeautifulSoup(html, "lxml")
            listings = self._parse_html_cards(soup)
        except Exception as e:
            print(f"[trademe] HTML card parse failed: {e}")

        return listings

    def _extract_from_next_data(self, data: dict) -> list[PropertyListing]:
        """Walk the Next.js page props to find listing arrays."""
        listings = []
        # Path varies by page version; try common paths
        try:
            props = data.get("props", {}).get("pageProps", {})
            # Try multiple possible keys
            results = (
                props.get("listings")
                or props.get("searchResults", {}).get("list")
                or props.get("data", {}).get("listings")
                or []
            )
            for item in results:
                listing = self._parse_listing_json(item)
                if listing:
                    listings.append(listing)
        except Exception as e:
            print(f"[trademe] next_data walk error: {e}")
        return listings

    def _parse_listing_json(self, item: dict) -> PropertyListing:
        """Parse a single listing from Trade Me's JSON structure."""
        try:
            listing_id = str(item.get("listingId") or item.get("id") or "")
            title = item.get("title") or item.get("name") or ""
            address_parts = [
                item.get("address", {}).get("suburb", ""),
                item.get("address", {}).get("district", ""),
                item.get("address", {}).get("region", ""),
            ]
            address = ", ".join(p for p in address_parts if p) or title

            price_val = item.get("buyNowPrice") or item.get("startPrice")
            price = float(price_val) if price_val else None
            price_display = item.get("priceDisplay") or (
                f"${price:,.0f}" if price else "Price on application"
            )

            region = extract_region(address)

            url = f"{self.base_url}/a/property/commercial/listing/{listing_id}"

            p = PropertyListing(
                id=make_id(self.source_name, url),
                source=self.source_name,
                title=title,
                address=address,
                region=region,
                url=url,
                price=price,
                price_display=price_display,
            )

            # Area data
            attrs = item.get("attributes") or []
            for attr in attrs:
                name = (attr.get("name") or "").lower()
                val = attr.get("value") or ""
                if "floor" in name:
                    p.floor_area = parse_area(str(val))
                elif "land" in name:
                    p.land_area = parse_area(str(val))
                elif "yield" in name:
                    p.yield_pct = parse_yield(str(val))

            p.description = item.get("subtitle") or item.get("description") or ""
            p.image_url = (
                (item.get("photos") or [{}])[0].get("value", {}).get("fullUrl", "")
                if item.get("photos")
                else ""
            )
            p.property_type = item.get("propertyType") or "Industrial"
            p.agent = (item.get("agency") or {}).get("name") or ""

            return p
        except Exception:
            return None

    def _parse_html_cards(self, soup: BeautifulSoup) -> list[PropertyListing]:
        """
        Fallback HTML card parser.
        Trade Me listing cards share common class patterns.
        """
        listings = []
        # Trade Me uses tg-card, tm-property-search-card, or similar class names
        cards = (
            soup.find_all("div", class_=re.compile(r"(listing-card|property-card|tm-card|tg-card)", re.I))
            or soup.find_all("li", class_=re.compile(r"(search-result|listing)", re.I))
        )

        for card in cards[:50]:
            try:
                # Title / link
                link_tag = card.find("a", href=re.compile(r"/property/"))
                if not link_tag:
                    continue
                title = link_tag.get_text(strip=True)
                href = link_tag.get("href", "")
                url = href if href.startswith("http") else self.base_url + href

                # Price
                price_tag = card.find(class_=re.compile(r"price", re.I))
                price_text = price_tag.get_text(strip=True) if price_tag else ""
                price = parse_price(price_text)

                # Address
                addr_tag = card.find(class_=re.compile(r"(address|suburb|location)", re.I))
                address = addr_tag.get_text(strip=True) if addr_tag else title
                region = extract_region(address)

                # Description
                desc_tag = card.find(class_=re.compile(r"(description|subtitle|summary)", re.I))
                description = desc_tag.get_text(strip=True) if desc_tag else ""

                p = PropertyListing(
                    id=make_id(self.source_name, url),
                    source=self.source_name,
                    title=title,
                    address=address,
                    region=region,
                    url=url,
                    price=price,
                    price_display=price_text or ("${:,.0f}".format(price) if price else "POA"),
                    description=description,
                )
                listings.append(p)
            except Exception:
                continue

        return listings
