"""
OneRoof Commercial scraper.
OneRoof (oneroof.co.nz) is NZME's real estate platform, aggregating listings
from many NZ agencies. They have a commercial property section.

Search URL:
  https://www.oneroof.co.nz/commercial?transactionType=sale&propertyType=industrial
"""
import asyncio
import json
import re
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, make_id, extract_region
from models import PropertyListing
from analyzer import parse_area, parse_price, parse_yield

SEARCH_URLS = [
    "https://www.oneroof.co.nz/commercial?transactionType=sale&propertyType=industrial",
    "https://www.oneroof.co.nz/commercial?transactionType=sale&propertyType=warehouse",
    "https://www.oneroof.co.nz/commercial?transactionType=sale&propertyType=industrial-land",
]


class OneRoofScraper(BaseScraper):
    source_name = "oneroof"
    base_url = "https://www.oneroof.co.nz"

    async def scrape(self, progress_callback=None) -> list[PropertyListing]:
        listings = []
        seen_ids = set()

        for i, url in enumerate(SEARCH_URLS):
            if progress_callback:
                progress_callback(f"OneRoof: fetching page {i + 1}/{len(SEARCH_URLS)}…")
            html = await self.fetch(url)
            if not html:
                continue

            page_listings = self._parse_page(html)
            for listing in page_listings:
                if listing.id not in seen_ids:
                    seen_ids.add(listing.id)
                    finalised = self.finalise_listing(listing)
                    if finalised:
                        listings.append(finalised)
            await asyncio.sleep(1.5)

        if progress_callback:
            progress_callback(f"OneRoof: found {len(listings)} industrial listings")
        return listings

    def _parse_page(self, html: str) -> list[PropertyListing]:
        listings = []
        soup = BeautifulSoup(html, "lxml")

        # Try to find embedded JSON (Next.js __NEXT_DATA__)
        next_data = soup.find("script", {"id": "__NEXT_DATA__"})
        if next_data:
            try:
                data = json.loads(next_data.string)
                props = data.get("props", {}).get("pageProps", {})
                results = (
                    props.get("listings")
                    or props.get("properties")
                    or props.get("searchResults", {}).get("properties")
                    or []
                )
                for item in results:
                    listing = self._parse_item(item)
                    if listing:
                        listings.append(listing)
                if listings:
                    return listings
            except Exception as e:
                print(f"[oneroof] __NEXT_DATA__ parse error: {e}")

        # Fallback HTML parsing
        cards = (
            soup.find_all("div", class_=re.compile(r"(listing|property|card)", re.I))
            or soup.find_all("article")
        )

        for card in cards[:40]:
            try:
                link = card.find("a", href=re.compile(r"/commercial/|/property/"))
                if not link:
                    continue
                href = link.get("href", "")
                url = href if href.startswith("http") else self.base_url + href
                title = link.get_text(strip=True) or ""

                price_tag = card.find(string=re.compile(r"\$[\d,]+"))
                price_text = str(price_tag).strip() if price_tag else ""
                price = parse_price(price_text)

                addr_tag = card.find(class_=re.compile(r"(address|suburb|location)", re.I))
                address = addr_tag.get_text(strip=True) if addr_tag else title
                region = extract_region(address)

                desc_tag = card.find(class_=re.compile(r"(desc|summary|details)", re.I))
                description = desc_tag.get_text(strip=True) if desc_tag else ""

                p = PropertyListing(
                    id=make_id(self.source_name, url),
                    source=self.source_name,
                    title=title,
                    address=address,
                    region=region,
                    url=url,
                    price=price,
                    price_display=price_text or (f"${price:,.0f}" if price else "POA"),
                    description=description,
                )
                listings.append(p)
            except Exception:
                continue

        return listings

    def _parse_item(self, item: dict) -> PropertyListing:
        try:
            url = item.get("url") or item.get("listingUrl") or ""
            if not url:
                listing_id = item.get("id") or item.get("listingId") or ""
                url = f"{self.base_url}/commercial/{listing_id}"

            title = item.get("title") or item.get("heading") or item.get("name") or ""
            address = item.get("address") or item.get("fullAddress") or title
            region = extract_region(address)

            price = None
            price_display = "Price on application"
            raw_price = item.get("price") or item.get("askingPrice")
            if raw_price:
                try:
                    price = float(str(raw_price).replace(",", "").replace("$", ""))
                    price_display = f"${price:,.0f}"
                except ValueError:
                    price_display = str(raw_price)

            yield_pct = parse_yield(str(item.get("yield") or ""))
            annual_rent = None
            rent_raw = item.get("annualRent") or item.get("rent")
            if rent_raw:
                try:
                    annual_rent = float(str(rent_raw).replace(",", "").replace("$", ""))
                except ValueError:
                    pass

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
                yield_display=f"{yield_pct:.1f}% yield" if yield_pct else "",
                floor_area=floor_area,
                land_area=land_area,
                description=item.get("description") or "",
                image_url=(item.get("images") or [{}])[0].get("url", "") if item.get("images") else "",
                agent=item.get("agentName") or "",
            )

            pt = (item.get("propertyType") or "").lower()
            if "land" in pt or "bare" in pt:
                p.is_bare_land = True
            if annual_rent or "lease" in p.description.lower():
                p.is_leased = True

            return p
        except Exception as e:
            print(f"[oneroof] item parse error: {e}")
            return None
