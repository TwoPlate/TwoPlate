"""
Demo data generator.
Produces realistic NZ industrial property listings for testing the UI
when live scrapers haven't been run yet or return no results.
These are fictional but representative examples.
"""
from models import PropertyListing
from analyzer import score_development_potential


DEMO_LISTINGS = [
    # --- High-yield leased investments ---
    {
        "id": "demo_001",
        "source": "demo",
        "title": "High-stud Warehouse — Leased Investment",
        "address": "14 Hamatana Road, Snells Beach, Auckland",
        "region": "Auckland",
        "url": "https://www.bayleys.co.nz/demo/001",
        "price": 3_250_000,
        "price_display": "$3,250,000",
        "annual_rent": 270_000,
        "floor_area": 1850,
        "land_area": 3200,
        "property_type": "Warehouse",
        "zoning": "Light Industrial",
        "description": (
            "Modern 1,850m² high-stud warehouse fully leased to an established "
            "logistics company. New 6-year lease in place with 2 rights of renewal. "
            "Net yield of 8.3%. Large sealed yard, 3-phase power, container wash-down bay."
        ),
        "is_leased": True,
        "lease_expiry": "2030",
        "agent": "Bayleys Commercial",
        "image_url": "",
        "listed_date": "2024-04-01",
    },
    {
        "id": "demo_002",
        "source": "demo",
        "title": "Industrial Investment — Long Lease, Hamilton",
        "address": "22 Sunshine Avenue, Te Rapa, Hamilton",
        "region": "Waikato",
        "url": "https://www.colliers.co.nz/demo/002",
        "price": 2_850_000,
        "price_display": "$2,850,000",
        "annual_rent": 215_000,
        "floor_area": 1200,
        "land_area": 2400,
        "property_type": "Industrial",
        "zoning": "General Industrial",
        "description": (
            "Solid 1,200m² workshop and warehouse leased to a national company "
            "on a 5+5 lease. Net yield of 7.5%. Excellent location in Te Rapa "
            "industrial precinct. Large hardstand yard, good truck access."
        ),
        "is_leased": True,
        "lease_expiry": "2029",
        "agent": "Colliers Hamilton",
        "image_url": "",
        "listed_date": "2024-03-20",
    },
    {
        "id": "demo_003",
        "source": "demo",
        "title": "Christchurch Distribution Centre — Net 7.1%",
        "address": "65 Waterloo Road, Hornby, Christchurch",
        "region": "Canterbury",
        "url": "https://www.bayleys.co.nz/demo/003",
        "price": 4_800_000,
        "price_display": "$4,800,000",
        "annual_rent": 340_800,
        "floor_area": 2500,
        "land_area": 5000,
        "property_type": "Warehouse / Distribution",
        "zoning": "General Industrial",
        "description": (
            "Modern 2,500m² distribution centre on a 5,000m² site in Hornby's "
            "prime industrial zone. Leased to a leading FMCG company on a new "
            "7-year term. Includes 400m² office, container-height roller doors, "
            "full sprinkler system."
        ),
        "is_leased": True,
        "lease_expiry": "2031",
        "agent": "Bayleys Canterbury",
        "image_url": "",
        "listed_date": "2024-02-15",
    },
    {
        "id": "demo_004",
        "source": "demo",
        "title": "Tauranga Industrial Unit — Leased",
        "address": "8 Wallace Crescent, Greerton, Tauranga",
        "region": "Bay of Plenty",
        "url": "https://www.trademe.co.nz/demo/004",
        "price": 1_450_000,
        "price_display": "$1,450,000",
        "annual_rent": 95_500,
        "floor_area": 520,
        "land_area": 900,
        "property_type": "Industrial Unit",
        "zoning": "Light Industrial",
        "description": (
            "510m² workshop unit, fully leased to a trade services company. "
            "6.6% net yield. Three-phase power, roller door access, small office "
            "and amenities. Good access to Port of Tauranga."
        ),
        "is_leased": True,
        "lease_expiry": "2027",
        "agent": "Ray White Commercial Bay of Plenty",
        "image_url": "",
        "listed_date": "2024-04-05",
    },
    {
        "id": "demo_005",
        "source": "demo",
        "title": "Napier Warehouse Investment — 6.8% Net",
        "address": "34 Ford Road, Onekawa, Napier",
        "region": "Hawke's Bay",
        "url": "https://www.colliers.co.nz/demo/005",
        "price": 2_100_000,
        "price_display": "$2,100,000",
        "annual_rent": 142_800,
        "floor_area": 1050,
        "land_area": 1800,
        "property_type": "Warehouse",
        "zoning": "General Industrial",
        "description": (
            "Well-presented 1,050m² warehouse in Napier's established Onekawa "
            "industrial precinct. New 4-year lease with rights of renewal. "
            "Net yield of 6.8%. Modern amenities, good natural light."
        ),
        "is_leased": True,
        "lease_expiry": "2028",
        "agent": "Colliers Napier",
        "image_url": "",
        "listed_date": "2024-03-10",
    },
    {
        "id": "demo_006",
        "source": "demo",
        "title": "Palmerston North Industrial — 6.4% Net Yield",
        "address": "101 Tremaine Avenue, Palmerston North",
        "region": "Manawatu-Whanganui",
        "url": "https://www.bayleys.co.nz/demo/006",
        "price": 1_780_000,
        "price_display": "$1,780,000",
        "annual_rent": 113_920,
        "floor_area": 840,
        "land_area": 1600,
        "property_type": "Industrial",
        "zoning": "Industrial",
        "description": (
            "840m² industrial building leased to a well-established local business "
            "on a 3+3 lease. Solid concrete construction, roller door, office wing. "
            "Good central Palmerston North location."
        ),
        "is_leased": True,
        "lease_expiry": "2027",
        "agent": "Bayleys Palmerston North",
        "image_url": "",
        "listed_date": "2024-01-20",
    },
    # --- Development potential listings ---
    {
        "id": "demo_007",
        "source": "demo",
        "title": "Prime Industrial Land — 8,500m² Bare Site, Auckland",
        "address": "Lot 4 Highbrook Drive, East Tamaki, Auckland",
        "region": "Auckland",
        "url": "https://www.colliers.co.nz/demo/007",
        "price": 5_200_000,
        "price_display": "$5,200,000",
        "annual_rent": None,
        "floor_area": None,
        "land_area": 8500,
        "property_type": "Industrial Land",
        "zoning": "Business - Light Industrial",
        "description": (
            "Rare 8,500m² bare industrial land in Highbrook Business Park — "
            "Auckland's premier industrial precinct. Fully serviced, resource consent "
            "available for up to 6,000m² warehouse. Excellent motorway access. "
            "Ideal for owner-occupier or build-to-lease development."
        ),
        "is_bare_land": True,
        "is_leased": False,
        "agent": "Colliers Auckland",
        "image_url": "",
        "listed_date": "2024-04-08",
    },
    {
        "id": "demo_008",
        "source": "demo",
        "title": "Industrial Development Site — 3,200m², Christchurch",
        "address": "Waterloo Business Park, Hornby, Christchurch",
        "region": "Canterbury",
        "url": "https://www.bayleys.co.nz/demo/008",
        "price": 1_650_000,
        "price_display": "$1,650,000",
        "annual_rent": None,
        "floor_area": None,
        "land_area": 3200,
        "property_type": "Industrial Land",
        "zoning": "General Industrial",
        "description": (
            "Fully serviced 3,200m² development site in Hornby's rapidly expanding "
            "business park. Vacant industrial land zoned General Industrial. "
            "Build your own purpose-built warehouse or factory. Services to boundary "
            "including 3-phase power and stormwater. Resource consent obtained for 1,800m² building."
        ),
        "is_bare_land": True,
        "is_leased": False,
        "agent": "Bayleys Canterbury",
        "image_url": "",
        "listed_date": "2024-03-25",
    },
    {
        "id": "demo_009",
        "source": "demo",
        "title": "Large Industrial Landholding — Redevelopment Opportunity, Wiri",
        "address": "85 Wiri Station Road, Wiri, Auckland",
        "region": "Auckland",
        "url": "https://www.trademe.co.nz/demo/009",
        "price": 7_800_000,
        "price_display": "$7,800,000",
        "annual_rent": 220_000,
        "floor_area": 1200,
        "land_area": 14500,
        "property_type": "Industrial",
        "zoning": "General Industrial",
        "description": (
            "Substantial 14,500m² industrial landholding in Wiri, Auckland's key "
            "industrial hub. Existing 1,200m² building leased (low rental, short term). "
            "Major redevelopment opportunity — very low site coverage of 8%. "
            "Subdivisible into multiple lots. Perfect for large-scale warehouse complex. "
            "Close to motorway interchange and Auckland Airport."
        ),
        "is_bare_land": False,
        "is_leased": True,
        "lease_expiry": "2025",
        "agent": "Colliers Auckland",
        "image_url": "",
        "listed_date": "2024-04-03",
    },
    {
        "id": "demo_010",
        "source": "demo",
        "title": "Hamilton Industrial Land — 5,000m² Build Your Own",
        "address": "Lot 12 Horotiu Road, Te Rapa, Hamilton",
        "region": "Waikato",
        "url": "https://www.bayleys.co.nz/demo/010",
        "price": 1_950_000,
        "price_display": "$1,950,000",
        "annual_rent": None,
        "floor_area": None,
        "land_area": 5000,
        "property_type": "Industrial Land",
        "zoning": "General Industrial",
        "description": (
            "5,000m² fully serviced bare industrial land in Te Rapa, Hamilton's "
            "primary industrial zone. Excellent access to State Highway 1. "
            "Surrounded by established industrial businesses. "
            "Ideal for warehouse, factory, or distribution centre. "
            "One of the last available lots in this popular development."
        ),
        "is_bare_land": True,
        "is_leased": False,
        "agent": "Bayleys Waikato",
        "image_url": "",
        "listed_date": "2024-02-28",
    },
    {
        "id": "demo_011",
        "source": "demo",
        "title": "Dunedin Industrial Site — Old Factory, Redevelopment Opportunity",
        "address": "12 Kaikorai Valley Road, Dunedin",
        "region": "Otago",
        "url": "https://www.colliers.co.nz/demo/011",
        "price": 980_000,
        "price_display": "$980,000",
        "annual_rent": None,
        "floor_area": 450,
        "land_area": 3800,
        "property_type": "Industrial",
        "zoning": "General Industrial",
        "description": (
            "3,800m² site with an old 450m² factory building (low site coverage — 12%). "
            "The existing building is dated and the real value is in the land. "
            "Zoned General Industrial. Demolish and rebuild a modern warehouse "
            "or develop multiple smaller units. Good vehicle access, flat site."
        ),
        "is_bare_land": False,
        "is_leased": False,
        "agent": "Colliers Dunedin",
        "image_url": "",
        "listed_date": "2024-03-05",
    },
    {
        "id": "demo_012",
        "source": "demo",
        "title": "Nelson Industrial Land — Corner Site, 2,100m²",
        "address": "Lot 3 Saxton Road, Nelson",
        "region": "Nelson",
        "url": "https://www.bayleys.co.nz/demo/012",
        "price": 890_000,
        "price_display": "$890,000",
        "annual_rent": None,
        "floor_area": None,
        "land_area": 2100,
        "property_type": "Industrial Land",
        "zoning": "Light Industrial",
        "description": (
            "Bare 2,100m² corner industrial site in Nelson's growing light industrial "
            "area. Services to boundary, flat contour. Ideal for a 1,000–1,200m² "
            "owner-occupier warehouse or trade premises. Resource consent "
            "can be provided to a purchaser with a suitable building design."
        ),
        "is_bare_land": True,
        "is_leased": False,
        "agent": "Bayleys Nelson",
        "image_url": "",
        "listed_date": "2024-04-10",
    },
    # --- Owner-occupier / value-add ---
    {
        "id": "demo_013",
        "source": "demo",
        "title": "Vacant Industrial Building — Owner-Occupier Opportunity",
        "address": "27 Portside Drive, Mount Maunganui, Tauranga",
        "region": "Bay of Plenty",
        "url": "https://www.trademe.co.nz/demo/013",
        "price": 2_200_000,
        "price_display": "$2,200,000",
        "annual_rent": None,
        "floor_area": 980,
        "land_area": 1800,
        "property_type": "Warehouse",
        "zoning": "Light Industrial",
        "description": (
            "Vacant 980m² high-stud warehouse available with vacant possession. "
            "Modern construction, large roller doors, 3-phase power. "
            "Ideal for owner-occupier wanting prime Bay of Plenty location. "
            "Close to Port of Tauranga. Could generate strong rent if leased."
        ),
        "is_bare_land": False,
        "is_leased": False,
        "agent": "Ray White Commercial",
        "image_url": "",
        "listed_date": "2024-04-12",
    },
    {
        "id": "demo_014",
        "source": "demo",
        "title": "Wellington Industrial Shed — Owner Occupy or Lease",
        "address": "52 Gracefield Road, Lower Hutt, Wellington",
        "region": "Wellington",
        "url": "https://www.bayleys.co.nz/demo/014",
        "price": 1_620_000,
        "price_display": "$1,620,000",
        "annual_rent": 95_000,
        "floor_area": 760,
        "land_area": 1200,
        "property_type": "Industrial",
        "zoning": "General Industrial",
        "description": (
            "760m² industrial shed in Gracefield, Lower Hutt's established industrial "
            "area. Owner is relocating and willing to enter a short leaseback. "
            "Potential yield ~5.9% if re-leased at market rates. "
            "Easy motorway access, yard area for vehicle storage."
        ),
        "is_bare_land": False,
        "is_leased": False,
        "agent": "Bayleys Wellington",
        "image_url": "",
        "listed_date": "2024-03-18",
    },
]


def get_demo_listings() -> list[PropertyListing]:
    """Return demo PropertyListing objects with calculated fields."""
    listings = []
    for data in DEMO_LISTINGS:
        p = PropertyListing(
            id=data["id"],
            source=data["source"],
            title=data["title"],
            address=data["address"],
            region=data["region"],
            url=data["url"],
            price=data.get("price"),
            price_display=data.get("price_display", "POA"),
            annual_rent=data.get("annual_rent"),
            floor_area=data.get("floor_area"),
            land_area=data.get("land_area"),
            property_type=data.get("property_type", "Industrial"),
            zoning=data.get("zoning", ""),
            description=data.get("description", ""),
            is_bare_land=data.get("is_bare_land", False),
            is_leased=data.get("is_leased", False),
            lease_expiry=data.get("lease_expiry", ""),
            image_url=data.get("image_url", ""),
            listed_date=data.get("listed_date", ""),
            agent=data.get("agent", ""),
        )
        p.calculate_yield()
        p.calculate_site_coverage()
        p.dev_score, p.dev_notes = score_development_potential(p)
        listings.append(p)
    return listings
