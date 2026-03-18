"""
Data models for NZ industrial property listings.
"""
from dataclasses import dataclass, field
from typing import Optional
import json


@dataclass
class PropertyListing:
    id: str
    source: str                         # e.g. "trademe", "bayleys", "colliers"
    title: str
    address: str
    region: str                         # e.g. "Auckland", "Wellington", "Canterbury"
    url: str

    price: Optional[float] = None       # NZD
    price_display: str = "Price on application"
    annual_rent: Optional[float] = None # NZD per year
    yield_pct: Optional[float] = None   # Net yield % (calculated or listed)
    yield_display: str = ""

    floor_area: Optional[float] = None  # m²
    land_area: Optional[float] = None   # m²
    site_coverage: Optional[float] = None  # floor_area / land_area ratio

    property_type: str = "Industrial"   # Industrial, Warehouse, Land, etc.
    zoning: str = ""
    description: str = ""
    features: list = field(default_factory=list)

    is_bare_land: bool = False          # True if land only, no buildings
    is_leased: bool = False             # True if tenanted (has yield potential)
    lease_expiry: str = ""

    # Development potential
    dev_score: float = 0.0              # 0-10 score
    dev_notes: list = field(default_factory=list)

    image_url: str = ""
    listed_date: str = ""
    agent: str = ""

    def calculate_yield(self):
        """Calculate yield if price and rent are known."""
        if self.price and self.annual_rent and self.price > 0:
            self.yield_pct = round((self.annual_rent / self.price) * 100, 2)
            self.yield_display = f"{self.yield_pct:.1f}% net yield"

    def calculate_site_coverage(self):
        """Calculate site coverage ratio."""
        if self.floor_area and self.land_area and self.land_area > 0:
            self.site_coverage = self.floor_area / self.land_area

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "title": self.title,
            "address": self.address,
            "region": self.region,
            "url": self.url,
            "price": self.price,
            "price_display": self.price_display,
            "annual_rent": self.annual_rent,
            "yield_pct": self.yield_pct,
            "yield_display": self.yield_display,
            "floor_area": self.floor_area,
            "land_area": self.land_area,
            "site_coverage": self.site_coverage,
            "property_type": self.property_type,
            "zoning": self.zoning,
            "description": self.description,
            "features": json.dumps(self.features),
            "is_bare_land": self.is_bare_land,
            "is_leased": self.is_leased,
            "lease_expiry": self.lease_expiry,
            "dev_score": self.dev_score,
            "dev_notes": json.dumps(self.dev_notes),
            "image_url": self.image_url,
            "listed_date": self.listed_date,
            "agent": self.agent,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PropertyListing":
        p = cls(
            id=d["id"],
            source=d["source"],
            title=d["title"],
            address=d["address"],
            region=d["region"],
            url=d["url"],
        )
        p.price = d.get("price")
        p.price_display = d.get("price_display", "Price on application")
        p.annual_rent = d.get("annual_rent")
        p.yield_pct = d.get("yield_pct")
        p.yield_display = d.get("yield_display", "")
        p.floor_area = d.get("floor_area")
        p.land_area = d.get("land_area")
        p.site_coverage = d.get("site_coverage")
        p.property_type = d.get("property_type", "Industrial")
        p.zoning = d.get("zoning", "")
        p.description = d.get("description", "")
        features = d.get("features", "[]")
        p.features = json.loads(features) if isinstance(features, str) else features
        p.is_bare_land = bool(d.get("is_bare_land", False))
        p.is_leased = bool(d.get("is_leased", False))
        p.lease_expiry = d.get("lease_expiry", "")
        p.dev_score = float(d.get("dev_score", 0.0))
        dev_notes = d.get("dev_notes", "[]")
        p.dev_notes = json.loads(dev_notes) if isinstance(dev_notes, str) else dev_notes
        p.image_url = d.get("image_url", "")
        p.listed_date = d.get("listed_date", "")
        p.agent = d.get("agent", "")
        return p
