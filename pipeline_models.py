"""
Data models for Kernohan Engineering Sales Pipeline.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from datetime import date, datetime


# ── Kernohan Engineering workstreams ──────────────────────────────────────────

WORKSTREAMS: dict[str, dict] = {
    "Marine Engineering": {
        "keywords": [
            "marine", "vessel", "ship", "boat", "fishing", "aquaculture",
            "port", "harbour", "harbor", "maritime", "wharf", "jetty",
            "pontoon", "trawl", "hull", "barge", "berth", "dry dock",
            "offshore", "buoy", "mooring",
        ],
        "description": "Vessel maintenance, fishing fleet, aquaculture, port infrastructure",
        "colour": "#0ea5e9",
    },
    "Structural & Fabrication": {
        "keywords": [
            "fabrication", "structural steel", "structural", "welding",
            "certified weld", "steel fabricat", "metal fabricat",
            "structural engineer", "steelwork", "metalwork", "ironwork",
            "bolted connection", "weld inspection",
        ],
        "description": "Structural steel, fabrication, certified welding",
        "colour": "#f97316",
    },
    "Plant & Maintenance": {
        "keywords": [
            "maintenance", "plant maintenance", "mechanical maintenance",
            "preventative maintenance", "industrial maintenance", "machinery",
            "equipment maintenance", "asset management", "uptime",
            "reliability", "planned maintenance", "servicing", "repair",
            "overhaul", "breakdown", "mechanical services",
        ],
        "description": "Industrial plant maintenance and uptime management",
        "colour": "#8b5cf6",
    },
    "Stainless Steel & Pipe": {
        "keywords": [
            "stainless", "stainless steel", "pipe", "pipework", "pipeline",
            "piping", "alloy", "mild steel", "process piping", "pipe fabricat",
            "pipe installation", "reticulation", "manifold", "fitting",
            "flange", "pressure vessel", "tank fabricat",
        ],
        "description": "Stainless/alloy fabrication, pipework installation",
        "colour": "#06b6d4",
    },
    "Machine Shop": {
        "keywords": [
            "machining", "machine shop", "precision machining", "turning",
            "milling", "CNC", "lathe", "machined component", "precision",
            "boring", "grinding", "thread",
        ],
        "description": "Precision machining and machine shop services",
        "colour": "#84cc16",
    },
    "Design & Build": {
        "keywords": [
            "design and build", "design build", "mechanical design",
            "engineering design", "design consultancy", "concept design",
            "detailed design", "d&b", "EPC", "project management",
            "engineering consultancy", "mechanical engineering",
        ],
        "description": "Mechanical design, project management, D&B",
        "colour": "#ec4899",
    },
    "Water & Wastewater": {
        "keywords": [
            "water treatment", "wastewater", "sewage", "sewer",
            "pump station", "water supply", "reticulation", "3 waters",
            "three waters", "stormwater", "reservoir", "water main",
            "treatment plant", "aeration", "filtration", "drinking water",
        ],
        "description": "Water/wastewater plant, pump stations, treatment",
        "colour": "#14b8a6",
    },
    "Industrial & Process": {
        "keywords": [
            "industrial", "process engineering", "food processing",
            "dairy", "timber", "forestry", "MDF", "manufacturing",
            "production", "processing plant", "cement", "mining",
            "oil", "gas", "fuel", "chemical", "wood processing",
        ],
        "description": "Industrial and resource/food processing sectors",
        "colour": "#f59e0b",
    },
}

# Regions where Kernohan has priority focus
PRIORITY_REGIONS = ["Nelson", "Tasman", "Marlborough", "West Coast", "Golden Bay"]

# All NZ regions for classification
NZ_REGIONS = [
    "Nelson", "Tasman", "Marlborough", "West Coast", "Golden Bay",
    "Canterbury", "Otago", "Southland", "Wellington", "Waikato",
    "Auckland", "Northland", "Bay of Plenty", "Gisborne",
    "Hawke's Bay", "Manawatu-Whanganui",
]

# Submission type full labels
SUBMISSION_TYPE_LABELS: dict[str, str] = {
    "TENDER":  "Tender (ITT/ITQ)",
    "ROFP":    "Request for Full Proposals",
    "ROI":     "Register of Interest",
    "EOI":     "Expression of Interest",
    "RFP":     "Request for Proposal",
    "RFQ":     "Request for Quotation",
    "GPN":     "General Procurement Notice",
    "PANEL":   "Panel / Pre-qualification",
    "OTHER":   "Other",
}

SUBMISSION_TYPE_COLOURS: dict[str, str] = {
    "TENDER": "#16a34a",
    "ROFP":   "#2563eb",
    "ROI":    "#7c3aed",
    "EOI":    "#0891b2",
    "RFP":    "#1d4ed8",
    "RFQ":    "#059669",
    "GPN":    "#78716c",
    "PANEL":  "#b45309",
    "OTHER":  "#374151",
}


# ── Opportunity model ─────────────────────────────────────────────────────────

@dataclass
class Opportunity:
    """A single procurement opportunity / tender prospect."""
    id: str                          # hash of title + agency + source
    title: str
    agency: str
    submission_type: str             # key from SUBMISSION_TYPE_LABELS
    closing_date: Optional[date]
    published_date: Optional[date]
    region: str
    url: str
    description: str = ""
    reference: str = ""              # RFx ID / reference number
    source: str = ""                 # gets, ncc, tdc, mdc, port_nelson, demo
    category: str = ""               # engineering, marine, civil, etc.
    workstream_tags: list[str] = field(default_factory=list)
    relevance_score: float = 0.0     # 0–10
    status: str = "open"             # open, closed, awarded
    last_seen: Optional[datetime] = None

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def days_until_closing(self) -> Optional[int]:
        if self.closing_date is None:
            return None
        return (self.closing_date - date.today()).days

    @property
    def closing_display(self) -> str:
        if self.closing_date is None:
            return "TBC"
        days = self.days_until_closing
        if days is None:
            return "TBC"
        if days < 0:
            return f"Closed {abs(days)}d ago"
        if days == 0:
            return "Closes TODAY"
        if days == 1:
            return "Closes tomorrow"
        if days <= 7:
            return f"Closes in {days} days"
        return self.closing_date.strftime("%-d %b %Y")

    @property
    def urgency(self) -> str:
        days = self.days_until_closing
        if days is None:
            return "unknown"
        if days < 0:
            return "closed"
        if days <= 3:
            return "critical"
        if days <= 7:
            return "urgent"
        if days <= 14:
            return "soon"
        return "open"

    @property
    def is_priority_region(self) -> bool:
        return any(r.lower() in self.region.lower() for r in PRIORITY_REGIONS)

    @property
    def type_label(self) -> str:
        return SUBMISSION_TYPE_LABELS.get(self.submission_type, self.submission_type)

    @property
    def type_colour(self) -> str:
        return SUBMISSION_TYPE_COLOURS.get(self.submission_type, "#374151")


# ── Helpers ───────────────────────────────────────────────────────────────────

def classify_submission_type(text: str) -> str:
    """Infer submission type from title or description text."""
    t = text.upper()
    if any(k in t for k in ("ROFP", "REQUEST FOR FULL PROPOSAL")):
        return "ROFP"
    if any(k in t for k in ("ROI", "REGISTER OF INTEREST", "REGISTRATION OF INTEREST")):
        return "ROI"
    if any(k in t for k in ("EOI", "EXPRESSION OF INTEREST")):
        return "EOI"
    if any(k in t for k in ("RFQ", "REQUEST FOR QUOTATION", "REQUEST FOR QUOTE", "INVITATION TO QUOTE", "ITQ")):
        return "RFQ"
    if any(k in t for k in ("RFP", "REQUEST FOR PROPOSAL")):
        return "RFP"
    if any(k in t for k in ("GPN", "GENERAL PROCUREMENT NOTICE", "ADVANCE NOTICE")):
        return "GPN"
    if any(k in t for k in ("PANEL", "PRE-QUALIF", "PREQUALIF", "FRAMEWORK")):
        return "PANEL"
    if any(k in t for k in ("TENDER", "ITT", "INVITATION TO TENDER")):
        return "TENDER"
    return "TENDER"  # default


def score_opportunity(opp: Opportunity) -> tuple[float, list[str]]:
    """
    Score 0–10 and return matched workstream tags.
    Factors: workstream match, priority region, urgency window, type weight.
    """
    text = f"{opp.title} {opp.description} {opp.category}".lower()
    matched: list[str] = []

    for ws_name, ws_info in WORKSTREAMS.items():
        if any(kw.lower() in text for kw in ws_info["keywords"]):
            matched.append(ws_name)

    score = 0.0
    # Workstream relevance (up to 5 pts)
    score += min(len(matched) * 1.5, 5.0)
    # Priority region bonus (2 pts)
    if opp.is_priority_region:
        score += 2.0
    # Submission type weight (up to 2 pts)
    type_weight = {
        "TENDER": 2.0, "RFQ": 1.8, "ROFP": 1.6, "RFP": 1.5,
        "EOI": 1.0, "ROI": 0.8, "PANEL": 1.2, "GPN": 0.5, "OTHER": 0.3,
    }
    score += type_weight.get(opp.submission_type, 0.5)
    # Still open bonus (1 pt)
    days = opp.days_until_closing
    if days is not None and days >= 0:
        score += 1.0

    return min(score, 10.0), matched


def detect_region(text: str) -> str:
    """Detect NZ region from text."""
    t = text.lower()
    for region in NZ_REGIONS:
        if region.lower() in t:
            return region
    return "Nationwide"
