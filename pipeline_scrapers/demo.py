"""
Realistic demo/seed data for the Kernohan Engineering Sales Pipeline.
Populated with representative NZ engineering procurement opportunities.
"""
from __future__ import annotations
from datetime import date, timedelta

from pipeline_models import Opportunity
from pipeline_database import make_id

TODAY = date.today()


def _days(n: int) -> date:
    return TODAY + timedelta(days=n)


def get_demo_opportunities() -> list[Opportunity]:
    return [
        # ── Tenders ────────────────────────────────────────────────────────────
        Opportunity(
            id=make_id("Nelson WWTP Mechanical Plant Maintenance Contract", "Nelson City Council", "demo"),
            title="Nelson Wastewater Treatment Plant – Mechanical Plant Maintenance Contract",
            agency="Nelson City Council",
            submission_type="TENDER",
            closing_date=_days(18),
            published_date=_days(-5),
            region="Nelson",
            url="https://www.gets.govt.nz/NCC/ExternalTenderDetails.htm?id=99001",
            description=(
                "Nelson City Council invites tenders for mechanical plant maintenance services "
                "at the Nelson Wastewater Treatment Plant, including pump maintenance, pipe work, "
                "stainless steel fabrication, and general plant upkeep. "
                "Term: 3 years + 2 × 1-year renewals."
            ),
            reference="NCC-2026-WW-001",
            source="demo",
            category="Mechanical Maintenance",
        ),
        Opportunity(
            id=make_id("Port Nelson Marine Infrastructure Maintenance", "Port Nelson", "demo"),
            title="Port Nelson – Marine Infrastructure Maintenance Services 2026–2029",
            agency="Port Nelson",
            submission_type="TENDER",
            closing_date=_days(25),
            published_date=_days(-3),
            region="Nelson",
            url="https://www.gets.govt.nz/PNLTD/ExternalTenderDetails.htm?id=99002",
            description=(
                "Port Nelson Limited seeks a contractor to provide ongoing marine infrastructure "
                "maintenance including wharf structural repairs, fendering systems, pipework, "
                "fabrication works, and mechanical maintenance of port equipment. "
                "Certified welding required to AS/NZS standards."
            ),
            reference="PNL-2026-INFRA-01",
            source="demo",
            category="Marine / Infrastructure",
        ),
        Opportunity(
            id=make_id("Maitai River Pump Station Upgrade", "Nelson City Council", "demo"),
            title="Maitai Dam – Pump Station Upgrade and Pipework Installation",
            agency="Nelson City Council",
            submission_type="TENDER",
            closing_date=_days(31),
            published_date=_days(-7),
            region="Nelson",
            url="https://www.gets.govt.nz/NCC/ExternalTenderDetails.htm?id=99003",
            description=(
                "Design and build of upgraded pump station at Maitai Dam including new submersible "
                "pumps, stainless steel manifold, associated pipework, mechanical fit-out, and "
                "commissioning. Scope includes structural steelwork for pump platforms."
            ),
            reference="NCC-2026-PS-002",
            source="demo",
            category="Water Supply / Civil",
        ),
        Opportunity(
            id=make_id("Rabbit Island Water Treatment Plant Maintenance", "Tasman District Council", "demo"),
            title="Rabbit Island Water Treatment Plant – Mechanical Maintenance Panel",
            agency="Tasman District Council",
            submission_type="TENDER",
            closing_date=_days(14),
            published_date=_days(-10),
            region="Tasman",
            url="https://www.tasman.govt.nz/my-business/tenders-and-supplier-panel",
            description=(
                "Tasman District Council seeks suitably experienced contractors for a mechanical "
                "maintenance panel covering the Rabbit Island and Waimea water treatment plants. "
                "Services include pump maintenance, pipe fabrication, stainless steel work, "
                "and general mechanical maintenance. Panel term to 30 June 2028."
            ),
            reference="TDC-2026-WTP-11",
            source="demo",
            category="Water Treatment / Maintenance",
        ),
        Opportunity(
            id=make_id("Marlborough Forestry Equipment Fabrication", "Marlborough District Council", "demo"),
            title="Marlborough District Council – Forestry Equipment Structural Fabrication",
            agency="Marlborough District Council",
            submission_type="TENDER",
            closing_date=_days(22),
            published_date=_days(-2),
            region="Marlborough",
            url="https://www.marlborough.govt.nz/your-council/tenders",
            description=(
                "Fabrication and supply of structural steel components for forestry road "
                "drainage structures, culvert headwalls, and vehicle bridges. "
                "Certified welding to structural grade. Delivery to Marlborough forests."
            ),
            reference="MDC-2026-FOR-07",
            source="demo",
            category="Structural Fabrication",
        ),
        Opportunity(
            id=make_id("Nelson Hospital Plant Room Mechanical Services", "Health NZ Nelson Marlborough", "demo"),
            title="Nelson Hospital – Plant Room Mechanical Services and Pipe Maintenance",
            agency="Health NZ – Nelson Marlborough",
            submission_type="TENDER",
            closing_date=_days(35),
            published_date=_days(-1),
            region="Nelson",
            url="https://www.gets.govt.nz/NMDHB/ClientOrganisationTenders.htm?action=open",
            description=(
                "Health New Zealand invites tenders for mechanical services at Nelson Hospital "
                "covering steam pipework, medical gas systems, plant room maintenance, "
                "stainless steel fabrication, and general engineering works. "
                "Must hold AS/NZS 4041 certification for pressure pipework."
            ),
            reference="HNZ-NM-2026-ENG-03",
            source="demo",
            category="Mechanical Services",
        ),

        # ── ROFP ──────────────────────────────────────────────────────────────
        Opportunity(
            id=make_id("Nelmac Infrastructure ROFP 2026", "Nelmac", "demo"),
            title="Nelmac – Request for Full Proposals: Engineering and Fabrication Services",
            agency="Nelmac",
            submission_type="ROFP",
            closing_date=_days(42),
            published_date=_days(-8),
            region="Nelson",
            url="https://www.gets.govt.nz/NELMAC/ExternalTenderDetails.htm?id=99010",
            description=(
                "Nelmac Limited (Nelson's water and infrastructure company) seeks ROFP responses "
                "for an engineering and fabrication services contract. Scope includes stainless "
                "steel tank fabrication, pipe installation, structural steelwork, and mechanical "
                "plant maintenance across Nelson/Tasman water infrastructure assets. "
                "Contract value estimated $500k–$2M per annum."
            ),
            reference="NML-2026-ENG-ROFP",
            source="demo",
            category="Engineering / Infrastructure",
        ),
        Opportunity(
            id=make_id("West Coast Regional Council Marine Structures ROFP", "West Coast Regional Council", "demo"),
            title="West Coast Regional Council – Marine Structures Maintenance ROFP",
            agency="West Coast Regional Council",
            submission_type="ROFP",
            closing_date=_days(48),
            published_date=_days(-4),
            region="West Coast",
            url="https://www.gets.govt.nz/WCRC/ExternalTenderDetails.htm?id=99011",
            description=(
                "WCRC invites full proposals for maintenance of coastal and riverine structures "
                "including jetties, boat ramps, flood gates, and river training works. "
                "Scope includes structural steel fabrication, marine-grade welding, and "
                "mechanical maintenance of flood control infrastructure."
            ),
            reference="WCRC-2026-MAR-ROFP",
            source="demo",
            category="Marine / Structural",
        ),

        # ── ROI ───────────────────────────────────────────────────────────────
        Opportunity(
            id=make_id("NZTA Nelson Region Roading ROI 2026", "Waka Kotahi NZTA", "demo"),
            title="Waka Kotahi – Nelson Region Roading Engineering Services ROI",
            agency="Waka Kotahi NZTA",
            submission_type="ROI",
            closing_date=_days(10),
            published_date=_days(-14),
            region="Nelson",
            url="https://www.gets.govt.nz/NZTA/ExternalTenderDetails.htm?id=99020",
            description=(
                "Waka Kotahi invites suitably qualified engineering contractors to register "
                "interest for roading infrastructure works in the Nelson/Tasman/Marlborough region. "
                "This ROI will establish a shortlist for future ITT/ROFP processes. "
                "Works include bridge maintenance, drainage structures, retaining walls, "
                "and structural steel bridge repairs."
            ),
            reference="NZTA-2026-ROI-NEL",
            source="demo",
            category="Roading / Civil Engineering",
        ),
        Opportunity(
            id=make_id("Port Nelson Dry Dock Facility ROI", "Port Nelson", "demo"),
            title="Port Nelson – Dry Dock Facility Engineering Services ROI",
            agency="Port Nelson",
            submission_type="ROI",
            closing_date=_days(7),
            published_date=_days(-21),
            region="Nelson",
            url="https://www.gets.govt.nz/PNLTD/ExternalTenderDetails.htm?id=99021",
            description=(
                "Port Nelson is seeking registrations of interest from engineering firms capable of "
                "providing dry dock facility management, vessel maintenance support, structural "
                "inspection and repair, marine engineering, and heavy fabrication services. "
                "Successful ROI registrants will be invited to tender."
            ),
            reference="PNL-2026-ROI-DD",
            source="demo",
            category="Marine Engineering",
        ),

        # ── EOI ───────────────────────────────────────────────────────────────
        Opportunity(
            id=make_id("TDC Three Waters Infrastructure EOI", "Tasman District Council", "demo"),
            title="Tasman District Council – Three Waters Infrastructure EOI: Engineering Services Panel",
            agency="Tasman District Council",
            submission_type="EOI",
            closing_date=_days(20),
            published_date=_days(-6),
            region="Tasman",
            url="https://www.tasman.govt.nz/my-business/tenders-and-supplier-panel",
            description=(
                "TDC is establishing a pre-qualified panel of engineering contractors for three "
                "waters infrastructure works including water mains, pump stations, reservoirs, "
                "and wastewater reticulation. EOI required to qualify for panel invitation. "
                "Contract value range: $50k–$2M. Panel term: 30 June 2028."
            ),
            reference="TDC-2026-3W-EOI",
            source="demo",
            category="Three Waters / Engineering",
        ),
        Opportunity(
            id=make_id("Nelson Aquaculture Infrastructure EOI", "Nelson City Council", "demo"),
            title="Nelson Aquaculture Precinct – Marine Engineering Support EOI",
            agency="Nelson City Council",
            submission_type="EOI",
            closing_date=_days(16),
            published_date=_days(-9),
            region="Nelson",
            url="https://ncc.govt.nz/business/tenders-and-procurement/current-tenders/",
            description=(
                "Nelson City Council invites expressions of interest from marine engineering "
                "firms to support development of the Nelson Aquaculture Precinct at Port Nelson. "
                "Services include jetty design and build, stainless pipework, pump systems, "
                "and ongoing marine infrastructure maintenance."
            ),
            reference="NCC-2026-AQ-EOI",
            source="demo",
            category="Marine / Aquaculture",
        ),

        # ── RFQ ───────────────────────────────────────────────────────────────
        Opportunity(
            id=make_id("Nelson Airport Stainless Steel Handrail RFQ", "Nelson Airport", "demo"),
            title="Nelson Airport – Stainless Steel Handrail and Balustrade RFQ",
            agency="Nelson Airport",
            submission_type="RFQ",
            closing_date=_days(9),
            published_date=_days(-5),
            region="Nelson",
            url="https://www.nelsonairport.co.nz/procurement",
            description=(
                "Nelson Airport Corporation seeks quotations for supply and installation of "
                "stainless steel handrails and balustrades throughout the terminal expansion. "
                "Marine-grade 316 stainless required. Site survey available by appointment."
            ),
            reference="NAC-2026-RFQ-047",
            source="demo",
            category="Stainless Steel Fabrication",
        ),
        Opportunity(
            id=make_id("MDC Wairau Irrigation Pipework RFQ", "Marlborough District Council", "demo"),
            title="Marlborough DC – Wairau Irrigation Scheme Pipework Replacement RFQ",
            agency="Marlborough District Council",
            submission_type="RFQ",
            closing_date=_days(12),
            published_date=_days(-3),
            region="Marlborough",
            url="https://www.marlborough.govt.nz/your-council/tenders",
            description=(
                "MDC seeks quotations for replacement of approximately 400m of mild steel irrigation "
                "pipework on the Wairau Plain, including supply of pipe, fittings, and installation. "
                "Works to be completed before irrigation season commences October 2026."
            ),
            reference="MDC-2026-RFQ-IRR",
            source="demo",
            category="Pipework / Civil",
        ),

        # ── GPN ───────────────────────────────────────────────────────────────
        Opportunity(
            id=make_id("GETS GPN Nelson Regional Industrial Maintenance Panel", "Nelson City Council", "demo"),
            title="Advance Notice – Nelson Regional Industrial Maintenance Panel (GPN)",
            agency="Nelson City Council",
            submission_type="GPN",
            closing_date=_days(60),
            published_date=_days(-2),
            region="Nelson",
            url="https://www.gets.govt.nz/NCC/ExternalTenderDetails.htm?id=99030",
            description=(
                "General Procurement Notice: Nelson City Council will be procuring an industrial "
                "maintenance services panel in Q3 2026. Scope will cover mechanical maintenance, "
                "fabrication, stainless and pipe work, and plant repairs for NCC infrastructure "
                "assets. Formal EOI/Tender to follow. Market engagement encouraged."
            ),
            reference="NCC-2026-GPN-MAINT",
            source="demo",
            category="Industrial Maintenance",
        ),

        # ── PANEL ─────────────────────────────────────────────────────────────
        Opportunity(
            id=make_id("Tasman DC Prequalified Contractor Panel Renewal", "Tasman District Council", "demo"),
            title="Tasman DC – Infrastructure Contractor Pre-qualification Panel Renewal 2026",
            agency="Tasman District Council",
            submission_type="PANEL",
            closing_date=_days(28),
            published_date=_days(-12),
            region="Tasman",
            url="https://www.tasman.govt.nz/my-business/tenders-and-supplier-panel",
            description=(
                "Tasman District Council is renewing its prequalified contractor framework for "
                "infrastructure works <$2M. Categories include civil/roading, structural/fabrication, "
                "three waters, and building services. Pre-qualified firms will be invited to "
                "price specific projects without open tender. Panel expires 30 June 2028."
            ),
            reference="TDC-2026-PANEL-RENEW",
            source="demo",
            category="Panel / Pre-qualification",
        ),
        Opportunity(
            id=make_id("Nelmac Mechanical Services Contractor Panel", "Nelmac", "demo"),
            title="Nelmac – Mechanical and Engineering Services Contractor Panel",
            agency="Nelmac",
            submission_type="PANEL",
            closing_date=_days(33),
            published_date=_days(-15),
            region="Nelson",
            url="https://www.gets.govt.nz/NELMAC/ExternalTenderDetails.htm?id=99031",
            description=(
                "Nelmac is establishing a mechanical and engineering services contractor panel for "
                "ongoing delivery of water/wastewater asset maintenance, pump station work, "
                "stainless steel fabrication, and civil works across Nelson/Tasman. "
                "Panel term: 3 years. Estimated annual spend: $1.5M–$3M."
            ),
            reference="NML-2026-PANEL-ME",
            source="demo",
            category="Mechanical / Engineering",
        ),

        # ── Future/Nationwide ──────────────────────────────────────────────────
        Opportunity(
            id=make_id("MBIE Engineering Services Nationwide Framework", "MBIE", "demo"),
            title="MBIE – Engineering and Technical Services All-of-Government Framework",
            agency="MBIE",
            submission_type="ROFP",
            closing_date=_days(55),
            published_date=_days(-20),
            region="Nationwide",
            url="https://www.gets.govt.nz/MBIE/ExternalTenderDetails.htm?id=99040",
            description=(
                "Ministry of Business, Innovation & Employment invites ROFP responses for an "
                "All-of-Government Engineering and Technical Services Framework. Categories include "
                "mechanical engineering, fabrication, infrastructure maintenance, and specialist "
                "industrial services. SME-friendly with regional lot structure."
            ),
            reference="MBIE-2026-AoG-ENG",
            source="demo",
            category="Engineering Services / AoG",
        ),
    ]
