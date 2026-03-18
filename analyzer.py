"""
Analyzes property listings to score yield and development potential.
"""
import re
from typing import Optional
from models import PropertyListing


# Keywords that indicate development potential (keyword -> score boost)
DEV_KEYWORDS = {
    "bare land": 4.0,
    "land only": 4.0,
    "vacant land": 4.0,
    "development site": 3.5,
    "development opportunity": 3.0,
    "subdivisible": 3.0,
    "resource consent": 3.0,
    "consent obtained": 3.0,
    "consent granted": 3.0,
    "build to suit": 2.5,
    "build your own": 2.5,
    "redevelopment": 2.5,
    "future development": 2.0,
    "develop": 1.5,
    "vacant possession": 1.5,
    "vacant site": 2.0,
    "greenfield": 2.5,
    "corner site": 0.5,
    "high stud": 0.3,
    "workshop": 0.2,
    "yard": 0.3,
    "hardstand": 0.5,
    "large site": 0.5,
    "surplus land": 2.0,
    "underdeveloped": 2.0,
    "low site coverage": 2.0,
    "warehouse and land": 1.0,
    "industrial land": 2.0,
    "zoned industrial": 1.5,
    "light industrial": 0.5,
    "heavy industrial": 0.5,
}

# Zoning strings that indicate industrial development potential
DEV_ZONINGS = {
    "industrial": 1.5,
    "light industrial": 1.0,
    "general industrial": 1.5,
    "heavy industrial": 1.5,
    "business - light industrial": 1.0,
    "mixed use": 0.5,
}


def score_development_potential(listing: PropertyListing) -> tuple[float, list[str]]:
    """
    Score a property's development potential from 0-10.
    Returns (score, list_of_reasons).
    """
    score = 0.0
    notes = []

    combined_text = (
        (listing.title + " " + listing.description + " " + listing.zoning).lower()
    )

    # 1. Bare land = highest development potential
    if listing.is_bare_land:
        score += 4.5
        notes.append("Bare land — build your own warehouse from scratch")
    elif listing.floor_area is None or listing.floor_area == 0:
        if listing.land_area and listing.land_area > 0:
            score += 4.0
            notes.append("No building area recorded — likely bare or mostly clear land")

    # 2. Site coverage ratio (lower = more room to develop)
    if listing.land_area and listing.floor_area and listing.land_area > 0:
        coverage = listing.floor_area / listing.land_area
        if coverage < 0.20:
            score += 3.0
            notes.append(
                f"Very low site coverage ({coverage:.0%}) — large portion of land undeveloped"
            )
        elif coverage < 0.35:
            score += 2.0
            notes.append(
                f"Low site coverage ({coverage:.0%}) — room to add more building area"
            )
        elif coverage < 0.50:
            score += 1.0
            notes.append(
                f"Moderate site coverage ({coverage:.0%}) — some development headroom"
            )

    # 3. Keyword scanning in title + description
    for keyword, boost in DEV_KEYWORDS.items():
        if keyword in combined_text:
            score += boost
            if boost >= 1.5:
                notes.append(f'Keyword match: "{keyword}"')

    # 4. Industrial zoning bonus
    for zone_text, boost in DEV_ZONINGS.items():
        if zone_text in listing.zoning.lower():
            score += boost
            break

    # 5. Large land area bonus (more land = more potential)
    if listing.land_area:
        if listing.land_area >= 10000:
            score += 1.5
            notes.append(f"Large site: {listing.land_area:,.0f}m² — scale development")
        elif listing.land_area >= 3000:
            score += 0.8
            notes.append(f"Good size site: {listing.land_area:,.0f}m²")
        elif listing.land_area >= 1000:
            score += 0.3

    # Cap at 10
    score = min(score, 10.0)
    return round(score, 1), notes


def score_yield(listing: PropertyListing) -> str:
    """Return a human-readable yield quality label."""
    if listing.yield_pct is None:
        return "unknown"
    if listing.yield_pct >= 8.0:
        return "excellent"
    if listing.yield_pct >= 6.5:
        return "good"
    if listing.yield_pct >= 5.0:
        return "average"
    return "low"


def dev_label(score: float) -> str:
    """Convert numeric dev score to a readable label."""
    if score >= 7.5:
        return "Prime Development"
    if score >= 5.0:
        return "Good Potential"
    if score >= 2.5:
        return "Some Potential"
    return "Established Property"


def parse_area(text: str) -> "Optional[float]":
    """Extract area in m² from a string like '1,250m²' or '0.5ha'."""
    if not text:
        return None
    text = text.replace(",", "").lower()
    # Hectares
    ha_match = re.search(r"([\d.]+)\s*ha", text)
    if ha_match:
        return float(ha_match.group(1)) * 10000
    # Square metres
    m2_match = re.search(r"([\d.]+)\s*m", text)
    if m2_match:
        return float(m2_match.group(1))
    return None


def parse_price(text: str) -> "Optional[float]":
    """Extract a numeric price from a display string."""
    if not text:
        return None
    text = text.replace(",", "").lower()
    # Millions shorthand: $2.8m
    m_match = re.search(r"\$?([\d.]+)\s*m", text)
    if m_match:
        return float(m_match.group(1)) * 1_000_000
    # Plain dollars
    d_match = re.search(r"\$?([\d]+)", text)
    if d_match:
        return float(d_match.group(1))
    return None


def parse_yield(text: str) -> "Optional[float]":
    """Extract yield percentage from text like '7.5% net yield'."""
    if not text:
        return None
    match = re.search(r"([\d.]+)\s*%", text)
    if match:
        return float(match.group(1))
    return None


