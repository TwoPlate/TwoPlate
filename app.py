"""
NZ Industrial Property Finder
Streamlit app that scrapes major NZ commercial real estate websites
for industrial properties for sale, ranked by yield and development potential.

Run with:  streamlit run app.py
"""
import asyncio
import sys
import os
from pathlib import Path

import streamlit as st
import pandas as pd

# Add project root to path so imports work
sys.path.insert(0, str(Path(__file__).parent))

from models import PropertyListing
from analyzer import dev_label, score_yield
from database import init_db, save_listings, load_listings, get_last_scrape_time, count_listings

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NZ Industrial Property Finder",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .prop-card {
        background: #1e2530;
        border: 1px solid #2d3748;
        border-radius: 10px;
        padding: 18px 20px;
        margin-bottom: 14px;
    }
    .prop-title { font-size: 1.05rem; font-weight: 700; margin-bottom: 4px; }
    .prop-address { color: #94a3b8; font-size: 0.88rem; margin-bottom: 10px; }
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-yield-excellent { background: #14532d; color: #86efac; }
    .badge-yield-good      { background: #164e63; color: #67e8f9; }
    .badge-yield-average   { background: #1e3a5f; color: #93c5fd; }
    .badge-yield-unknown   { background: #374151; color: #d1d5db; }
    .badge-dev-prime   { background: #7c2d12; color: #fdba74; }
    .badge-dev-good    { background: #713f12; color: #fde68a; }
    .badge-dev-some    { background: #365314; color: #bef264; }
    .badge-dev-estab   { background: #1e2a3a; color: #94a3b8; }
    .badge-source  { background: #1e293b; color: #64748b; font-size: 0.72rem; }
    .prop-meta { font-size: 0.9rem; color: #cbd5e1; margin-top: 8px; }
    .prop-desc { font-size: 0.85rem; color: #94a3b8; margin-top: 8px; line-height: 1.5; }
    .dev-note { font-size: 0.82rem; color: #fdba74; margin-top: 4px; }
    .section-header { font-size: 1.3rem; font-weight: 700; margin: 20px 0 14px 0; }
    .stat-box {
        background: #1e2530;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        border: 1px solid #2d3748;
    }
    .stat-num { font-size: 2rem; font-weight: 800; color: #60a5fa; }
    .stat-label { font-size: 0.82rem; color: #94a3b8; margin-top: 2px; }
    a { color: #60a5fa !important; text-decoration: none; }
    a:hover { text-decoration: underline; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def yield_badge(listing: PropertyListing) -> str:
    quality = score_yield(listing)
    label_map = {
        "excellent": ("EXCELLENT YIELD", "yield-excellent"),
        "good":      ("GOOD YIELD",      "yield-good"),
        "average":   ("AVG YIELD",       "yield-average"),
        "unknown":   ("NO YIELD DATA",   "yield-unknown"),
    }
    label, cls = label_map[quality]
    text = listing.yield_display or label
    return f'<span class="badge badge-{cls}">{text}</span>'


def dev_badge(listing: PropertyListing) -> str:
    label = dev_label(listing.dev_score)
    cls_map = {
        "Prime Development": "dev-prime",
        "Good Potential":    "dev-good",
        "Some Potential":    "dev-some",
        "Established Property": "dev-estab",
    }
    cls = cls_map.get(label, "dev-estab")
    return f'<span class="badge badge-{cls}">{label} ({listing.dev_score:.1f}/10)</span>'


def source_badge(source: str) -> str:
    labels = {
        "trademe": "Trade Me",
        "bayleys": "Bayleys",
        "colliers": "Colliers",
        "oneroof": "OneRoof",
        "demo": "Demo Data",
    }
    return f'<span class="badge badge-source">{labels.get(source, source.title())}</span>'


def format_area(m2: float) -> str:
    if m2 is None:
        return "—"
    if m2 >= 10000:
        return f"{m2 / 10000:.2f}ha ({m2:,.0f}m²)"
    return f"{m2:,.0f}m²"


def render_property_card(listing: PropertyListing, show_dev_notes: bool = False):
    """Render a single property as a styled HTML card."""
    # Truncate description
    desc = listing.description
    if len(desc) > 320:
        desc = desc[:320] + "…"

    # Meta line
    meta_parts = []
    if listing.price_display:
        meta_parts.append(f"<strong>{listing.price_display}</strong>")
    if listing.floor_area:
        meta_parts.append(f"Floor: {format_area(listing.floor_area)}")
    if listing.land_area:
        meta_parts.append(f"Land: {format_area(listing.land_area)}")
    if listing.agent:
        meta_parts.append(f"Agent: {listing.agent}")
    meta_str = " &nbsp;|&nbsp; ".join(meta_parts)

    # Dev notes
    dev_notes_html = ""
    if show_dev_notes and listing.dev_notes:
        notes_html = "".join(
            f'<div class="dev-note">• {note}</div>'
            for note in listing.dev_notes[:3]
        )
        dev_notes_html = notes_html

    card_html = f"""
    <div class="prop-card">
        <div class="prop-title">
            <a href="{listing.url}" target="_blank">{listing.title}</a>
        </div>
        <div class="prop-address">📍 {listing.address} &nbsp;·&nbsp; {listing.region}</div>
        <div>
            {yield_badge(listing)}
            {dev_badge(listing)}
            {source_badge(listing.source)}
        </div>
        <div class="prop-meta">{meta_str}</div>
        {f'<div class="prop-desc">{desc}</div>' if desc else ''}
        {dev_notes_html}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


async def run_scrapers(progress_placeholder, status_text):
    """Run all scrapers and return combined listing list."""
    from scrapers import ALL_SCRAPERS

    all_listings = []
    for ScraperClass in ALL_SCRAPERS:
        scraper = ScraperClass()
        name = scraper.source_name.title()

        def make_callback(n):
            def callback(msg):
                status_text.text(msg)
            return callback

        try:
            status_text.text(f"Starting {name} scraper…")
            listings = await scraper.scrape(progress_callback=make_callback(name))
            all_listings.extend(listings)
            status_text.text(f"{name} done — {len(listings)} listings found.")
        except Exception as e:
            status_text.text(f"{name} failed: {e}")

    return all_listings


def load_data(use_demo_fallback: bool = True) -> list[PropertyListing]:
    """Load listings from DB, falling back to demo data if DB is empty."""
    init_db()
    listings = load_listings()
    if not listings and use_demo_fallback:
        from scrapers.demo import get_demo_listings
        listings = get_demo_listings()
    return listings


def filter_listings(
    listings: list[PropertyListing],
    regions: list[str],
    min_price: float,
    max_price: float,
    min_yield: float,
    min_land: float,
    sources: list[str],
) -> list[PropertyListing]:
    out = []
    for p in listings:
        if regions and p.region not in regions:
            continue
        if p.price:
            if p.price < min_price or p.price > max_price:
                continue
        if min_yield > 0 and (p.yield_pct is None or p.yield_pct < min_yield):
            continue
        if min_land > 0 and (p.land_area is None or p.land_area < min_land):
            continue
        if sources and p.source not in sources:
            continue
        out.append(p)
    return out


# ── App Layout ────────────────────────────────────────────────────────────────

def main():
    # Header
    st.markdown("# 🏭 NZ Industrial Property Finder")
    st.markdown(
        "Scrapes Trade Me, Bayleys, Colliers, and OneRoof for **industrial properties for sale** across New Zealand. "
        "Ranked by investment yield and development potential."
    )
    st.divider()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## Scraper")
        last_updated = get_last_scrape_time()
        st.caption(f"Last updated: {last_updated}")
        st.caption(f"Listings in database: {count_listings()}")

        if st.button("🔄 Run Scraper (fetch live data)", use_container_width=True):
            with st.spinner("Scraping in progress…"):
                progress_bar = st.progress(0)
                status = st.empty()

                async def _run():
                    listings = await run_scrapers(progress_bar, status)
                    return listings

                listings = asyncio.run(_run())

                if listings:
                    save_listings(listings)
                    st.success(f"Done! Saved {len(listings)} listings.")
                else:
                    st.warning(
                        "Scrapers returned no results. Sites may have changed "
                        "their HTML structure, or they blocked the request. "
                        "Showing demo data below."
                    )
                st.rerun()

        st.markdown("## Filters")

        all_listings = load_data()
        all_regions = sorted(set(p.region for p in all_listings))
        all_sources = sorted(set(p.source for p in all_listings))

        selected_regions = st.multiselect(
            "Region", all_regions, default=[], placeholder="All regions"
        )
        selected_sources = st.multiselect(
            "Source", all_sources, default=[], placeholder="All sources"
        )

        max_price_cap = 20_000_000
        price_range = st.slider(
            "Price range (NZD)",
            0, max_price_cap,
            (0, max_price_cap),
            step=100_000,
            format="$%d",
        )

        min_yield = st.slider("Minimum yield %", 0.0, 12.0, 0.0, 0.1)
        min_land = st.slider("Minimum land area (m²)", 0, 20000, 0, 100)

        st.markdown("---")
        st.markdown(
            "**Tip:** The scraper fetches real listings from NZ property sites. "
            "Results depend on what's currently listed. "
            "Demo data is shown when no scraped data is available."
        )
        st.markdown(
            "Built to search: Trade Me · Bayleys · Colliers NZ · OneRoof"
        )

    # ── Main content ──────────────────────────────────────────────────────────
    listings = load_data()
    listings = filter_listings(
        listings,
        selected_regions,
        price_range[0],
        price_range[1],
        min_yield,
        min_land,
        selected_sources,
    )

    # Stats row
    col1, col2, col3, col4 = st.columns(4)
    with_yield = [p for p in listings if p.yield_pct]
    dev_potential = [p for p in listings if p.dev_score >= 5.0]
    avg_yield = (
        sum(p.yield_pct for p in with_yield) / len(with_yield)
        if with_yield else 0
    )
    bare_land = [p for p in listings if p.is_bare_land]

    with col1:
        st.markdown(
            f'<div class="stat-box"><div class="stat-num">{len(listings)}</div>'
            f'<div class="stat-label">Total Listings</div></div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div class="stat-box"><div class="stat-num">{len(with_yield)}</div>'
            f'<div class="stat-label">With Yield Data</div></div>',
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f'<div class="stat-box"><div class="stat-num">'
            f'{"%.1f" % avg_yield}%</div>'
            f'<div class="stat-label">Average Yield</div></div>',
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f'<div class="stat-box"><div class="stat-num">{len(bare_land)}</div>'
            f'<div class="stat-label">Bare Land / Dev Sites</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_yield, tab_dev, tab_all = st.tabs([
        "📈 By Yield",
        "🏗️ Development Potential",
        "📋 All Listings",
    ])

    # ── TAB 1: By Yield ───────────────────────────────────────────────────────
    with tab_yield:
        st.markdown(
            "Properties sorted by **net yield** — highest first. "
            "Only properties with price and rent data can be yield-ranked. "
            "Bare land and owner-occupier properties appear at the bottom."
        )

        # Sort: yield first, then unknowns
        yielded = sorted(
            [p for p in listings if p.yield_pct],
            key=lambda p: p.yield_pct,
            reverse=True,
        )
        no_yield = [p for p in listings if not p.yield_pct]

        if not yielded and not no_yield:
            st.info("No listings match your current filters.")
        else:
            if yielded:
                st.markdown(
                    f'<div class="section-header">Investment Properties ({len(yielded)})</div>',
                    unsafe_allow_html=True,
                )
                for listing in yielded:
                    render_property_card(listing, show_dev_notes=False)

            if no_yield:
                with st.expander(
                    f"Properties without yield data ({len(no_yield)}) — "
                    "owner-occupier / POA / bare land",
                    expanded=False,
                ):
                    for listing in no_yield:
                        render_property_card(listing, show_dev_notes=False)

    # ── TAB 2: Development Potential ─────────────────────────────────────────
    with tab_dev:
        st.markdown(
            "Properties scored for **development potential** — bare industrial land, "
            "sites with low building coverage, and properties with existing resource consents. "
            "Ideal for buying land and building a new warehouse."
        )

        dev_sorted = sorted(listings, key=lambda p: p.dev_score, reverse=True)
        prime = [p for p in dev_sorted if p.dev_score >= 7.5]
        good = [p for p in dev_sorted if 5.0 <= p.dev_score < 7.5]
        some = [p for p in dev_sorted if 2.5 <= p.dev_score < 5.0]
        estab = [p for p in dev_sorted if p.dev_score < 2.5]

        if not dev_sorted:
            st.info("No listings match your current filters.")

        if prime:
            st.markdown(
                f'<div class="section-header">🟠 Prime Development Sites ({len(prime)})</div>',
                unsafe_allow_html=True,
            )
            st.caption(
                "Bare land, resource consents, or very low site coverage — "
                "ideal for building a new warehouse."
            )
            for listing in prime:
                render_property_card(listing, show_dev_notes=True)

        if good:
            st.markdown(
                f'<div class="section-header">🟡 Good Development Potential ({len(good)})</div>',
                unsafe_allow_html=True,
            )
            for listing in good:
                render_property_card(listing, show_dev_notes=True)

        if some:
            with st.expander(f"Some Development Potential ({len(some)})", expanded=False):
                for listing in some:
                    render_property_card(listing, show_dev_notes=True)

        if estab:
            with st.expander(
                f"Established Properties — low dev potential ({len(estab)})",
                expanded=False,
            ):
                for listing in estab:
                    render_property_card(listing, show_dev_notes=False)

    # ── TAB 3: All Listings ───────────────────────────────────────────────────
    with tab_all:
        sort_by = st.selectbox(
            "Sort by",
            ["Yield (high → low)", "Dev Score (high → low)", "Price (low → high)", "Price (high → low)", "Most Recent"],
        )

        if sort_by == "Yield (high → low)":
            sorted_listings = sorted(
                listings,
                key=lambda p: (p.yield_pct is not None, p.yield_pct or 0),
                reverse=True,
            )
        elif sort_by == "Dev Score (high → low)":
            sorted_listings = sorted(listings, key=lambda p: p.dev_score, reverse=True)
        elif sort_by == "Price (low → high)":
            sorted_listings = sorted(
                listings,
                key=lambda p: (p.price is None, p.price or float("inf")),
            )
        elif sort_by == "Price (high → low)":
            sorted_listings = sorted(
                listings,
                key=lambda p: (p.price is None, -(p.price or 0)),
            )
        else:
            sorted_listings = sorted(
                listings, key=lambda p: p.listed_date or "", reverse=True
            )

        # Show as table option
        show_table = st.checkbox("Show as table instead of cards")

        if show_table and sorted_listings:
            rows = []
            for p in sorted_listings:
                rows.append({
                    "Title": p.title,
                    "Address": p.address,
                    "Region": p.region,
                    "Price": p.price_display,
                    "Yield": p.yield_display or "—",
                    "Floor Area": format_area(p.floor_area) if p.floor_area else "—",
                    "Land Area": format_area(p.land_area) if p.land_area else "—",
                    "Dev Score": f"{p.dev_score:.1f}/10",
                    "Type": p.property_type,
                    "Source": p.source.title(),
                    "URL": p.url,
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            if not sorted_listings:
                st.info("No listings match your current filters.")
            for listing in sorted_listings:
                render_property_card(listing, show_dev_notes=True)

    # Footer
    st.divider()
    st.caption(
        "Data scraped from publicly available NZ real estate listings. "
        "Always verify details directly with the listing agent before making investment decisions. "
        "Yield calculations are estimates only."
    )


if __name__ == "__main__":
    main()
