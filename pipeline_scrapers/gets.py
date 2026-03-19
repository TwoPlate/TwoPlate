"""
Scraper for GETS (Government Electronic Tender Service) - gets.govt.nz.

Targets:
  - Main public tender list
  - Nelson City Council tenders
  - Port Nelson tenders
  - Tasman District Council (via GETS)
  - Marlborough District Council (via GETS)
  - Health NZ Nelson Marlborough
  - Waka Kotahi / NZTA engineering relevant tenders

GETS serves a publicly-viewable tender list without requiring login for
the summary data. Individual tender details require registration, but
the list view is open.
"""
from __future__ import annotations
import re
import logging
from datetime import date, datetime
from typing import Callable, Optional

from pipeline_models import (
    Opportunity,
    classify_submission_type,
    detect_region,
)
from pipeline_database import make_id
from pipeline_scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# GETS organisation codes relevant to Kernohan
GETS_ORG_PAGES = [
    # (org_code, display_name, region)
    ("NCC",    "Nelson City Council",                    "Nelson"),
    ("PNLTD",  "Port Nelson",                            "Nelson"),
    ("TDC",    "Tasman District Council",                "Tasman"),
    ("MDC",    "Marlborough District Council",           "Marlborough"),
    ("NMDHB",  "Health NZ – Nelson Marlborough",         "Nelson"),
    ("NELMAC", "Nelmac (Nelson water/infrastructure)",   "Nelson"),
    ("WCRC",   "West Coast Regional Council",            "West Coast"),
    ("NZTA",   "Waka Kotahi NZTA",                       "Nationwide"),
    ("MBIE",   "MBIE",                                   "Nationwide"),
    ("MOD",    "Ministry of Defence",                    "Nationwide"),
]

GETS_BASE = "https://www.gets.govt.nz"

# Engineering-relevant keywords to filter the broader GETS list
ENGINEERING_KEYWORDS = [
    "engineer", "fabricat", "structural", "mechanical", "marine",
    "vessel", "ship", "maintenance", "plant", "pipe", "stainless",
    "welding", "machining", "water", "wastewater", "pump", "civil",
    "construction", "infrastructure", "industrial", "processing",
    "timber", "forestry", "dairy", "fishing", "aquaculture", "port",
    "harbour", "refurbish", "upgrade", "install", "electrical",
    "asset", "facilities", "building services",
]


def _parse_gets_date(raw: str) -> Optional[date]:
    """Parse GETS date formats: '15 Apr 2026', '15/04/2026', ISO etc."""
    raw = raw.strip()
    for fmt in ("%d %b %Y", "%d/%m/%Y", "%Y-%m-%d", "%d %B %Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    return None


def _is_relevant(title: str, description: str = "") -> bool:
    text = f"{title} {description}".lower()
    return any(kw in text for kw in ENGINEERING_KEYWORDS)


class GETSScraper(BaseScraper):
    source_name = "gets"
    display_name = "GETS (NZ Govt Tenders)"
    base_url = GETS_BASE

    async def scrape(
        self,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> list[Opportunity]:
        opps: list[Opportunity] = []

        # 1. Scrape GETS main public tender list (filtered by engineering)
        self._cb(progress_callback, "Fetching GETS main tender list…")
        main_opps = await self._scrape_main_list()
        opps.extend(main_opps)
        self._cb(progress_callback, f"GETS main list: {len(main_opps)} engineering opportunities.")

        # 2. Scrape each organisation-specific page
        for org_code, org_name, region in GETS_ORG_PAGES:
            self._cb(progress_callback, f"Fetching {org_name}…")
            org_opps = await self._scrape_org_page(org_code, org_name, region)
            # De-duplicate by title+agency
            existing_keys = {(o.title, o.agency) for o in opps}
            new_opps = [o for o in org_opps if (o.title, o.agency) not in existing_keys]
            opps.extend(new_opps)
            self._cb(progress_callback, f"{org_name}: {len(new_opps)} opportunities.")

        await self.close()
        return opps

    # ── Main public list ──────────────────────────────────────────────────────

    async def _scrape_main_list(self) -> list[Opportunity]:
        url = f"{GETS_BASE}/ExternalTenderList.htm"
        soup = await self._fetch(url)
        if soup is None:
            soup = await self._fetch_playwright(url)
        if soup is None:
            logger.warning("[gets] Could not fetch main tender list.")
            return []
        return self._parse_tender_table(soup, default_region=None)

    # ── Org-specific page ─────────────────────────────────────────────────────

    async def _scrape_org_page(
        self, org_code: str, org_name: str, region: str
    ) -> list[Opportunity]:
        url = f"{GETS_BASE}/{org_code}/ClientOrganisationTenders.htm?action=open"
        soup = await self._fetch(url)
        if soup is None:
            soup = await self._fetch_playwright(url)
        if soup is None:
            return []
        opps = self._parse_tender_table(soup, default_region=region, default_agency=org_name)
        return opps

    # ── Table parser ──────────────────────────────────────────────────────────

    def _parse_tender_table(
        self,
        soup,
        default_region: Optional[str],
        default_agency: str = "",
    ) -> list[Opportunity]:
        """Parse any GETS-style tender table."""
        opps: list[Opportunity] = []

        # GETS renders rows inside a table with class "tenderList" or similar
        # Rows contain: RFx ID | Title | Agency | Category | Closing Date | Type
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue

            # Detect header positions
            header_cells = rows[0].find_all(["th", "td"])
            header_text = [c.get_text(strip=True).lower() for c in header_cells]

            col_idx = {
                "title": _find_col(header_text, ["title", "description", "tender"]),
                "agency": _find_col(header_text, ["agency", "organisation", "client"]),
                "closing": _find_col(header_text, ["closing", "close", "due", "deadline"]),
                "type": _find_col(header_text, ["type", "rfx type", "category"]),
                "ref": _find_col(header_text, ["rfx id", "reference", "id", "ref"]),
            }

            if col_idx["title"] is None:
                continue  # not a tender table

            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) < 2:
                    continue

                def cell_text(idx):
                    if idx is None or idx >= len(cells):
                        return ""
                    return cells[idx].get_text(" ", strip=True)

                def cell_link(idx):
                    if idx is None or idx >= len(cells):
                        return ""
                    a = cells[idx].find("a", href=True)
                    if a:
                        href = a["href"]
                        if href.startswith("http"):
                            return href
                        return GETS_BASE + "/" + href.lstrip("/")
                    return ""

                title = cell_text(col_idx["title"])
                if not title or title.lower() in ("title", "description"):
                    continue

                agency = cell_text(col_idx["agency"]) or default_agency
                raw_closing = cell_text(col_idx["closing"])
                raw_type = cell_text(col_idx["type"])
                reference = cell_text(col_idx["ref"])
                url = cell_link(col_idx["title"]) or cell_link(col_idx["ref"])

                if not _is_relevant(title):
                    continue

                closing_date = _parse_gets_date(raw_closing)
                region = default_region or detect_region(f"{title} {agency}")
                sub_type = classify_submission_type(f"{raw_type} {title}")

                opp = Opportunity(
                    id=make_id(title, agency, "gets"),
                    title=title,
                    agency=agency,
                    submission_type=sub_type,
                    closing_date=closing_date,
                    published_date=None,
                    region=region,
                    url=url or f"{GETS_BASE}/ExternalTenderList.htm",
                    description="",
                    reference=reference,
                    source="gets",
                    category=raw_type,
                )
                opps.append(opp)

        return opps


def _find_col(headers: list[str], keywords: list[str]) -> Optional[int]:
    for i, h in enumerate(headers):
        if any(k in h for k in keywords):
            return i
    return None


# ── Council-direct scrapers ───────────────────────────────────────────────────

class NelsonCityCouncilScraper(BaseScraper):
    """Nelson City Council procurement page (separate from GETS)."""
    source_name = "ncc"
    display_name = "Nelson City Council"
    base_url = "https://ncc.govt.nz"

    async def scrape(self, progress_callback=None) -> list[Opportunity]:
        self._cb(progress_callback, "Fetching Nelson City Council tenders…")
        url = "https://ncc.govt.nz/business/tenders-and-procurement/current-tenders/"
        soup = await self._fetch(url)
        if soup is None:
            soup = await self._fetch_playwright(url)
        if soup is None:
            self._cb(progress_callback, "NCC: Could not fetch page.")
            await self.close()
            return []

        opps = self._parse_ncc(soup)
        self._cb(progress_callback, f"NCC: {len(opps)} opportunities found.")
        await self.close()
        return opps

    def _parse_ncc(self, soup) -> list[Opportunity]:
        opps = []
        # NCC typically lists tenders in a table or dl/definition list
        for item in soup.select("table tr, .tender-item, article, .entry"):
            text = item.get_text(" ", strip=True)
            if not text or len(text) < 10:
                continue
            a_tag = item.find("a", href=True)
            title = a_tag.get_text(strip=True) if a_tag else text[:120]
            if not title or not _is_relevant(title, text):
                continue
            href = a_tag["href"] if a_tag else ""
            if href and not href.startswith("http"):
                href = self.base_url + href

            closing_date = _extract_date_from_text(text)
            sub_type = classify_submission_type(title + " " + text)

            opp = Opportunity(
                id=make_id(title, "Nelson City Council", "ncc"),
                title=title,
                agency="Nelson City Council",
                submission_type=sub_type,
                closing_date=closing_date,
                published_date=None,
                region="Nelson",
                url=href or self.base_url,
                description=text[:400],
                source="ncc",
                category="",
            )
            opps.append(opp)
        return opps


class TasmanDistrictCouncilScraper(BaseScraper):
    source_name = "tdc"
    display_name = "Tasman District Council"
    base_url = "https://www.tasman.govt.nz"

    async def scrape(self, progress_callback=None) -> list[Opportunity]:
        self._cb(progress_callback, "Fetching Tasman District Council tenders…")
        urls = [
            "https://www.tasman.govt.nz/my-business/tenders-and-supplier-panel",
            "https://www.tasman.govt.nz/council/council-information/tenders/",
        ]
        opps = []
        for url in urls:
            soup = await self._fetch(url)
            if soup is None:
                soup = await self._fetch_playwright(url)
            if soup:
                opps.extend(self._parse_council_generic(soup, "Tasman District Council", "Tasman", url))
        self._cb(progress_callback, f"TDC: {len(opps)} opportunities found.")
        await self.close()
        return opps

    def _parse_council_generic(self, soup, agency, region, base_url):
        opps = []
        seen_titles = set()
        for item in soup.select("table tr, li, .tender, article, .entry, .field-item"):
            text = item.get_text(" ", strip=True)
            if len(text) < 20:
                continue
            a_tag = item.find("a", href=True)
            title = a_tag.get_text(strip=True) if a_tag else text[:120]
            title = re.sub(r'\s+', ' ', title).strip()
            if not title or title in seen_titles:
                continue
            if not _is_relevant(title, text):
                continue
            seen_titles.add(title)
            href = a_tag["href"] if a_tag else ""
            if href and not href.startswith("http"):
                href = base_url.rstrip("/") + "/" + href.lstrip("/")
            closing_date = _extract_date_from_text(text)
            sub_type = classify_submission_type(title + " " + text)
            opp = Opportunity(
                id=make_id(title, agency, self.source_name),
                title=title,
                agency=agency,
                submission_type=sub_type,
                closing_date=closing_date,
                published_date=None,
                region=region,
                url=href or base_url,
                description=text[:400],
                source=self.source_name,
                category="",
            )
            opps.append(opp)
        return opps


class MarlboroughDistrictCouncilScraper(BaseScraper):
    source_name = "mdc"
    display_name = "Marlborough District Council"
    base_url = "https://www.marlborough.govt.nz"

    async def scrape(self, progress_callback=None) -> list[Opportunity]:
        self._cb(progress_callback, "Fetching Marlborough District Council tenders…")
        url = "https://www.marlborough.govt.nz/your-council/tenders"
        soup = await self._fetch(url)
        if soup is None:
            soup = await self._fetch_playwright(url)
        if soup is None:
            self._cb(progress_callback, "MDC: Could not fetch page.")
            await self.close()
            return []

        opps = TasmanDistrictCouncilScraper._parse_council_generic(
            self, soup, "Marlborough District Council", "Marlborough", url
        )
        self._cb(progress_callback, f"MDC: {len(opps)} opportunities found.")
        await self.close()
        return opps


class PortNelsonScraper(BaseScraper):
    source_name = "port_nelson"
    display_name = "Port Nelson"
    base_url = "https://www.portnelson.co.nz"

    async def scrape(self, progress_callback=None) -> list[Opportunity]:
        self._cb(progress_callback, "Fetching Port Nelson tenders…")
        # Port Nelson uses GETS; also check their own site
        urls = [
            f"{GETS_BASE}/PNLTD/ClientOrganisationTenders.htm",
            "https://www.portnelson.co.nz/about-port-nelson/procurement/",
        ]
        opps = []
        for url in urls:
            soup = await self._fetch(url)
            if soup is None:
                soup = await self._fetch_playwright(url)
            if soup:
                opps.extend(
                    TasmanDistrictCouncilScraper._parse_council_generic(
                        self, soup, "Port Nelson", "Nelson", url
                    )
                )
        self._cb(progress_callback, f"Port Nelson: {len(opps)} opportunities found.")
        await self.close()
        return opps


# ── Date extraction helper ────────────────────────────────────────────────────

_DATE_PATTERNS = [
    r"\b(\d{1,2})[/ ](\w{3,9})[/ ](\d{4})\b",     # 15 Apr 2026 / 15/Apr/2026
    r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b",             # 15/04/2026
    r"\b(\d{4})-(\d{2})-(\d{2})\b",                 # 2026-04-15
]

_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
}


def _extract_date_from_text(text: str) -> Optional[date]:
    text_lower = text.lower()
    # Closing label clue: look near "clos" / "due" / "deadline"
    for pattern in _DATE_PATTERNS:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        for m in matches:
            try:
                g = m.groups()
                if len(g) == 3:
                    if "-" in m.group():
                        return date(int(g[0]), int(g[1]), int(g[2]))
                    if "/" in m.group() and g[1].isdigit():
                        return date(int(g[2]), int(g[1]), int(g[0]))
                    # day month_str year
                    month = _MONTH_MAP.get(g[1].lower()[:3])
                    if month:
                        return date(int(g[2]), month, int(g[0]))
            except (ValueError, KeyError):
                pass
    return None
