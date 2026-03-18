"""
Colliers NZ scraper.
Colliers is a major international commercial real estate firm with a strong NZ presence.

They expose a public search API:
  https://www.colliers.co.nz/api/search/properties
  with query parameters for property type, sale method, country, etc.
"""
import asyncio
import re
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, make_id, extract_region
from models import PropertyListing
from analyzer import parse_area, parse_price, parse_yield

# Colliers public API endpoint
API_BASE = "https://www.colliers.co.nz/api/search/properties"

SEARCH_PAGES = [
    "https://www.colliers.co.nz/en-nz/properties/for-sale?propertyType=Industrial,Warehouse&pageSize=24",
    "https://www.colliers.co.nz/en-nz/properties/for-sale?propertyType=Industrial+Land&pageSize=24",
]


class ColliersScraper(BaseScraper):
    source_name = "colliers"
    base_url = "https://www.colliers.co.nz"

    async def scrape(self, progress_callback=None) -> list[PropertyListing]:
        listings = []
        seen_ids = set()

        if progress_callback:
            progress_callback("Colliers: querying listings API…")

        api_listings = await self._scrape_api()
        for listing in api_listings:
            if listing.id not in seen_ids:
                seen_ids.add(listing.id)
                finalised = self.finalise_listing(listing)
                if finalised:
                    listings.append(finalised)

        # Fallback to HTML if API fails
        if not listings:
            for i, url in enumerate(SEARCH_PAGES):
                if progress_callback:
                    progress_callback(f"Colliers: scraping page {i + 1}/{len(SEARCH_PAGES)}…")
                html = await self.fetch(url)
                if html:
                    for listing in self._parse_html(html):
                        if listing.id not in seen_ids:
                            seen_ids.add(listing.id)
                            finalised = self.finalise_listing(listing)
                            if finalised:
                                listings.append(finalised)
                await asyncio.sleep(1.5)

        if progress_callback:
            progress_callback(f"Colliers: found {len(listings)} industrial listings")
        return listings

    async def _scrape_api(self) -> list[PropertyListing]:
        listings = []
        for page in range(1, 4):
            params = {
                "country": "nz",
                "saleType": "sale",
                "propertyType": "Industrial,Warehouse,IndustrialLand",
                "page": page,
                "pageSize": 24,
                "sortBy": "datePosted",
                "sortOrder": "desc",
            }
            data = await self.fetch_json(API_BASE, params=params)
            if not data:
                break

            items = (
                data.get("properties")
                or data.get("listings")
                or data.get("results")
                or (data.get("data") or {}).get("properties")
                or []
            )
            if not items:
                break

            for item in items:
                listing = self._parse_item(item)
                if listing:
                    listings.append(listing)

            total = data.get("totalCount") or data.get("total") or 0
            if page * 24 >= total:
                break
            await asyncio.sleep(1.0)

        return listings

    def _parse_item(self, item: dict) -> PropertyListing:
        try:
            # Build URL
            slug = item.get("slug") or item.get("propertyId") or item.get("id") or ""
            url = f"{self.base_url}/en-nz/properties/{slug}" if slug else ""
            if not url:
                url = item.get("url") or ""
            if not url:
                return None

            title = item.get("name") or item.get("heading") or item.get("title") or ""
            address = (
                item.get("fullAddress")
                or item.get("address")
                or item.get("streetAddress")
                or title
            )
            region = extract_region(
                address + " " + (item.get("region") or item.get("suburb") or "")
            )

            # Price
            price = None
            price_display = "Price on application"
            for price_key in ("askingPrice", "price", "listingPrice", "salePrice"):
                raw = item.get(price_key)
                if raw:
                    try:
                        price = float(str(raw).replace(",", "").replace("$", ""))
                        price_display = f"${price:,.0f}"
                    except ValueError:
                        price_display = str(raw)
                    break

            # Yield
            yield_pct = None
            yield_display = ""
            for ykey in ("netYield", "yield", "returnOnInvestment"):
                raw = item.get(ykey)
                if raw:
                    yield_pct = parse_yield(str(raw))
                    if yield_pct:
                        yield_display = f"{yield_pct:.1f}% net yield"
                    break

            # Annual rent
            annual_rent = None
            for rkey in ("annualRent", "currentRent", "rentalIncome"):
                raw = item.get(rkey)
                if raw:
                    try:
                        annual_rent = float(str(raw).replace(",", "").replace("$", ""))
                    except ValueError:
                        pass
                    break

            # Areas
            floor_area = None
            land_area = None
            for fkey in ("totalFloorArea", "floorArea", "buildingArea"):
                raw = item.get(fkey)
                if raw:
                    floor_area = parse_area(str(raw))
                    break
            for lkey in ("landArea", "siteArea", "lotSize"):
                raw = item.get(lkey)
                if raw:
                    land_area = parse_area(str(raw))
                    break

            property_type = item.get("propertyType") or item.get("subType") or "Industrial"

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
                yield_display=yield_display,
                floor_area=floor_area,
                land_area=land_area,
                property_type=property_type,
                description=item.get("description") or item.get("summary") or "",
                image_url=(item.get("images") or [{}])[0].get("url", "") if item.get("images") else "",
                zoning=item.get("zoning") or "",
                agent=item.get("agentName") or (item.get("agents") or [{}])[0].get("name", "") if item.get("agents") else "",
            )

            # Bare land detection
            pt_lower = (property_type + " " + title + " " + p.description).lower()
            if any(t in pt_lower for t in ["land only", "bare land", "vacant land", "industrial land"]):
                p.is_bare_land = True

            # Leased detection
            if annual_rent or "lease" in p.description.lower() or item.get("isLeased"):
                p.is_leased = True
                p.lease_expiry = str(item.get("leaseExpiry") or "")

            return p
        except Exception as e:
            print(f"[colliers] parse error: {e}")
            return None

    def _parse_html(self, html: str) -> list[PropertyListing]:
        soup = BeautifulSoup(html, "lxml")
        listings = []

        cards = (
            soup.find_all("div", class_=re.compile(r"(property-card|listing-card|search-result)", re.I))
            or soup.find_all("article", class_=re.compile(r"(property|listing)", re.I))
        )

        for card in cards[:40]:
            try:
                link = card.find("a", href=True)
                if not link:
                    continue
                href = link.get("href", "")
                url = href if href.startswith("http") else self.base_url + href
                title = link.get_text(strip=True) or ""

                price_tag = card.find(string=re.compile(r"\$[\d,]+"))
                price_text = str(price_tag).strip() if price_tag else ""
                price = parse_price(price_text)

                yield_tag = card.find(string=re.compile(r"\d+\.?\d*\s*%"))
                yield_text = str(yield_tag).strip() if yield_tag else ""
                yield_pct = parse_yield(yield_text)

                address_tag = card.find(class_=re.compile(r"(address|location|suburb)", re.I))
                address = address_tag.get_text(strip=True) if address_tag else title
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
