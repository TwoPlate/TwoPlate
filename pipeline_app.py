"""
Kernohan Engineering – Sales Pipeline & Prospecting Tool
=========================================================
Scrapes NZ procurement portals (GETS, local councils, Port Nelson) for
engineering opportunities relevant to Kernohan Engineering in Nelson.

Lists prospects by submission type (Tender, ROFP, ROI, EOI, RFQ, GPN…)
and closing date. Auto-refreshes every Monday at 4 pm NZST/NZDT.

Run with:  streamlit run pipeline_app.py
"""
from __future__ import annotations
import asyncio
import sys
import os
from pathlib import Path
from datetime import date, datetime
from zoneinfo import ZoneInfo

import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from pipeline_models import (
    Opportunity,
    SUBMISSION_TYPE_LABELS,
    SUBMISSION_TYPE_COLOURS,
    WORKSTREAMS,
    PRIORITY_REGIONS,
)
from pipeline_database import (
    init_db,
    save_opportunities,
    load_opportunities,
    log_scrape,
    get_last_scrape_time,
    count_opportunities,
)

NZT = ZoneInfo("Pacific/Auckland")

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Kernohan Engineering – Sales Pipeline",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
  /* App background */
  [data-testid="stAppViewContainer"] { background: #0f1117; }
  [data-testid="stSidebar"] { background: #161b27; }

  /* Cards */
  .opp-card {
    background: #1a2035;
    border: 1px solid #2a3350;
    border-radius: 10px;
    padding: 16px 18px;
    margin-bottom: 12px;
    transition: border-color 0.2s;
  }
  .opp-card:hover { border-color: #3d5a8a; }
  .opp-card.priority { border-left: 4px solid #f97316; }

  .opp-title { font-size: 1.0rem; font-weight: 700; color: #e2e8f0; margin-bottom: 3px; }
  .opp-agency { color: #94a3b8; font-size: 0.85rem; margin-bottom: 8px; }
  .opp-desc { font-size: 0.83rem; color: #8899aa; line-height: 1.5; margin-top: 8px; }
  .opp-ref { font-size: 0.75rem; color: #64748b; margin-top: 6px; }

  /* Badges */
  .badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 20px;
    font-size: 0.74rem;
    font-weight: 600;
    margin-right: 5px;
    margin-bottom: 3px;
  }
  .badge-type-TENDER  { background:#14532d; color:#86efac; }
  .badge-type-ROFP    { background:#1e3a8a; color:#93c5fd; }
  .badge-type-ROI     { background:#4c1d95; color:#c4b5fd; }
  .badge-type-EOI     { background:#164e63; color:#67e8f9; }
  .badge-type-RFP     { background:#1e3a8a; color:#bfdbfe; }
  .badge-type-RFQ     { background:#065f46; color:#6ee7b7; }
  .badge-type-GPN     { background:#374151; color:#d1d5db; }
  .badge-type-PANEL   { background:#78350f; color:#fde68a; }
  .badge-type-OTHER   { background:#374151; color:#9ca3af; }

  .badge-urgency-critical { background:#7f1d1d; color:#fca5a5; }
  .badge-urgency-urgent   { background:#7c2d12; color:#fdba74; }
  .badge-urgency-soon     { background:#713f12; color:#fde68a; }
  .badge-urgency-open     { background:#1e293b; color:#94a3b8; }
  .badge-urgency-closed   { background:#111827; color:#4b5563; }
  .badge-urgency-unknown  { background:#1e293b; color:#64748b; }

  .badge-region-priority { background:#0c4a6e; color:#7dd3fc; }
  .badge-region-other    { background:#1e293b; color:#64748b; }
  .badge-ws              { background:#1e293b; color:#a5b4fc; font-size:0.7rem; }
  .badge-score-high      { background:#14532d; color:#86efac; }
  .badge-score-mid       { background:#1e3a5f; color:#93c5fd; }
  .badge-score-low       { background:#374151; color:#9ca3af; }

  /* Section headers */
  .section-header {
    font-size: 1.2rem; font-weight: 700;
    margin: 20px 0 12px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid #2a3350;
    color: #e2e8f0;
  }

  /* Stat boxes */
  .stat-box {
    background: #1a2035;
    border: 1px solid #2a3350;
    border-radius: 8px;
    padding: 14px;
    text-align: center;
  }
  .stat-num   { font-size: 1.9rem; font-weight: 800; color: #60a5fa; }
  .stat-label { font-size: 0.78rem; color: #94a3b8; margin-top: 2px; }

  /* Urgency bar */
  .urgency-bar {
    background: #1a2035;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 12px;
  }

  a { color: #60a5fa !important; text-decoration: none; }
  a:hover { text-decoration: underline; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def type_badge(opp: Opportunity) -> str:
    label = SUBMISSION_TYPE_LABELS.get(opp.submission_type, opp.submission_type)
    cls = f"badge-type-{opp.submission_type}"
    return f'<span class="badge {cls}">{label}</span>'


def urgency_badge(opp: Opportunity) -> str:
    u = opp.urgency
    labels = {
        "critical": f"🔴 {opp.closing_display}",
        "urgent":   f"🟠 {opp.closing_display}",
        "soon":     f"🟡 {opp.closing_display}",
        "open":     f"🟢 {opp.closing_display}",
        "closed":   f"⚫ {opp.closing_display}",
        "unknown":  "⚪ Closing TBC",
    }
    return f'<span class="badge badge-urgency-{u}">{labels.get(u, opp.closing_display)}</span>'


def region_badge(opp: Opportunity) -> str:
    if opp.is_priority_region:
        return f'<span class="badge badge-region-priority">📍 {opp.region}</span>'
    return f'<span class="badge badge-region-other">📍 {opp.region}</span>'


def score_badge(opp: Opportunity) -> str:
    s = opp.relevance_score
    if s >= 7:
        cls = "badge-score-high"
    elif s >= 4:
        cls = "badge-score-mid"
    else:
        cls = "badge-score-low"
    return f'<span class="badge {cls}">★ {s:.1f}/10</span>'


def ws_badges(opp: Opportunity) -> str:
    if not opp.workstream_tags:
        return ""
    return "".join(
        f'<span class="badge badge-ws">{ws}</span>'
        for ws in opp.workstream_tags[:3]
    )


def render_opportunity_card(opp: Opportunity, show_desc: bool = True) -> None:
    priority_cls = "opp-card priority" if opp.is_priority_region else "opp-card"
    desc_html = ""
    if show_desc and opp.description:
        desc = opp.description[:300] + "…" if len(opp.description) > 300 else opp.description
        desc_html = f'<div class="opp-desc">{desc}</div>'
    ref_html = f'<div class="opp-ref">Ref: {opp.reference} &nbsp;|&nbsp; Source: {opp.source.upper()}</div>' if opp.reference else ""
    card = f"""
    <div class="{priority_cls}">
        <div class="opp-title">
            <a href="{opp.url}" target="_blank">{opp.title}</a>
        </div>
        <div class="opp-agency">{opp.agency}</div>
        <div>
            {type_badge(opp)}
            {urgency_badge(opp)}
            {region_badge(opp)}
            {score_badge(opp)}
        </div>
        <div style="margin-top:5px">{ws_badges(opp)}</div>
        {desc_html}
        {ref_html}
    </div>"""
    st.markdown(card, unsafe_allow_html=True)


# ── Scraper runner ────────────────────────────────────────────────────────────

async def run_all_scrapers(status_text) -> list[Opportunity]:
    from pipeline_scrapers import ALL_SCRAPERS
    all_opps: list[Opportunity] = []
    for ScraperClass in ALL_SCRAPERS:
        scraper = ScraperClass()

        def cb(msg, name=scraper.display_name):
            status_text.text(f"[{name}] {msg}")

        try:
            opps = await scraper.scrape(progress_callback=cb)
            all_opps.extend(opps)
        except Exception as exc:
            status_text.text(f"[{scraper.display_name}] Error: {exc}")
    return all_opps


def do_scrape(status_text) -> tuple[int, str]:
    opps = asyncio.run(run_all_scrapers(status_text))
    if opps:
        saved = save_opportunities(opps)
        log_scrape("all", saved)
        return saved, "live"
    # Fall back to demo
    from pipeline_scrapers.demo import get_demo_opportunities
    demo_opps = get_demo_opportunities()
    saved = save_opportunities(demo_opps)
    log_scrape("demo", saved, "scrapers returned no results – demo loaded")
    return saved, "demo"


# ── Data loading ──────────────────────────────────────────────────────────────

def load_data(include_closed: bool = False) -> list[Opportunity]:
    init_db()
    opps = load_opportunities(include_closed=include_closed)
    if not opps:
        from pipeline_scrapers.demo import get_demo_opportunities
        opps = get_demo_opportunities()
        save_opportunities(opps)
        log_scrape("demo", len(opps), "initial demo data load")
        opps = load_opportunities(include_closed=include_closed)
    return opps


# ── Scheduler info ────────────────────────────────────────────────────────────

def next_monday_4pm_nzt() -> str:
    from datetime import timedelta
    now = datetime.now(tz=NZT)
    days_until_monday = (7 - now.weekday()) % 7  # 0=Monday
    if days_until_monday == 0 and now.hour >= 16:
        days_until_monday = 7  # already past 4pm Monday
    next_monday = now + timedelta(days=days_until_monday)
    next_run = next_monday.replace(hour=16, minute=0, second=0, microsecond=0)
    return next_run.strftime("%-d %b %Y at 4:00 pm NZST")


# ── Filter helpers ────────────────────────────────────────────────────────────

def filter_opportunities(
    opps: list[Opportunity],
    selected_types: list[str],
    selected_regions: list[str],
    selected_workstreams: list[str],
    selected_sources: list[str],
    min_score: float,
    show_closed: bool,
) -> list[Opportunity]:
    out = []
    for o in opps:
        if selected_types and o.submission_type not in selected_types:
            continue
        if selected_regions and o.region not in selected_regions:
            continue
        if selected_workstreams and not any(ws in o.workstream_tags for ws in selected_workstreams):
            continue
        if selected_sources and o.source not in selected_sources:
            continue
        if o.relevance_score < min_score:
            continue
        if not show_closed and o.urgency == "closed":
            continue
        out.append(o)
    return out


# ── Main app ──────────────────────────────────────────────────────────────────

def main():
    # ── Header ────────────────────────────────────────────────────────────────
    col_logo, col_title = st.columns([1, 8])
    with col_logo:
        st.markdown("# ⚙️")
    with col_title:
        st.markdown("## Kernohan Engineering")
        st.markdown(
            "<span style='color:#94a3b8;font-size:0.95rem'>"
            "Sales Pipeline & Prospecting Tool &nbsp;·&nbsp; Nelson, NZ"
            "</span>",
            unsafe_allow_html=True,
        )
    st.divider()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ Pipeline Controls")

        last_updated = get_last_scrape_time()
        st.caption(f"Last scraped: {last_updated or 'Never'}")
        st.caption(f"Opportunities stored: {count_opportunities()}")
        st.caption(f"Next auto-refresh: {next_monday_4pm_nzt()}")

        if st.button("🔄 Scrape Now", use_container_width=True, type="primary"):
            with st.spinner("Scraping procurement portals…"):
                status = st.empty()
                count, mode = do_scrape(status)
                if mode == "live":
                    st.success(f"Done! {count} opportunities saved from live sources.")
                else:
                    st.warning(
                        f"Live scrapers returned no results (sites may require login or have changed). "
                        f"Loaded {count} demo opportunities instead."
                    )
            st.rerun()

        st.divider()
        st.markdown("### 🔍 Filters")

        all_opps = load_data(include_closed=True)
        all_types    = sorted(set(o.submission_type for o in all_opps))
        all_regions  = sorted(set(o.region for o in all_opps))
        all_ws       = sorted(set(ws for o in all_opps for ws in o.workstream_tags))
        all_sources  = sorted(set(o.source for o in all_opps))

        selected_types = st.multiselect(
            "Submission Type", all_types,
            format_func=lambda t: SUBMISSION_TYPE_LABELS.get(t, t),
            default=[], placeholder="All types",
        )
        selected_regions = st.multiselect(
            "Region", all_regions, default=[], placeholder="All regions",
        )
        selected_workstreams = st.multiselect(
            "Workstream", all_ws, default=[], placeholder="All workstreams",
        )
        selected_sources = st.multiselect(
            "Source", all_sources, default=[], placeholder="All sources",
        )
        min_score = st.slider("Min relevance score", 0.0, 10.0, 0.0, 0.5)
        show_closed = st.checkbox("Show closed opportunities", value=False)

        st.divider()
        st.markdown("**Sources scraped:**")
        for s in ["GETS (NZ Govt Tenders)", "Nelson City Council", "Tasman DC", "Marlborough DC", "Port Nelson"]:
            st.caption(f"• {s}")

    # ── Load and filter ───────────────────────────────────────────────────────
    all_opps = load_data(include_closed=show_closed)
    filtered = filter_opportunities(
        all_opps, selected_types, selected_regions,
        selected_workstreams, selected_sources, min_score, show_closed,
    )

    # ── Stats row ─────────────────────────────────────────────────────────────
    total = len(filtered)
    critical_urgent = [o for o in filtered if o.urgency in ("critical", "urgent")]
    priority_region = [o for o in filtered if o.is_priority_region]
    high_relevance  = [o for o in filtered if o.relevance_score >= 7.0]
    closing_week    = [o for o in filtered if o.days_until_closing is not None and 0 <= o.days_until_closing <= 7]

    c1, c2, c3, c4, c5 = st.columns(5)
    for col, num, label in [
        (c1, total,            "Total Prospects"),
        (c2, len(critical_urgent), "🔴 Close Soon (≤7d)"),
        (c3, len(priority_region), "📍 Priority Region"),
        (c4, len(high_relevance),  "★ High Relevance"),
        (c5, len(closing_week),    "⏰ This Week"),
    ]:
        col.markdown(
            f'<div class="stat-box"><div class="stat-num">{num}</div>'
            f'<div class="stat-label">{label}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_urgent, tab_type, tab_workstream, tab_all, tab_export = st.tabs([
        "🔴 Urgent / Closing",
        "📂 By Submission Type",
        "🔧 By Workstream",
        "📋 All Prospects",
        "📤 Export",
    ])

    # ── TAB 1: Urgent ─────────────────────────────────────────────────────────
    with tab_urgent:
        st.markdown(
            "Opportunities sorted by **closing date** — most urgent first. "
            "Orange border = Nelson/Tasman/Marlborough/West Coast priority region."
        )
        urgency_order = {"critical": 0, "urgent": 1, "soon": 2, "open": 3, "unknown": 4, "closed": 5}
        sorted_opps = sorted(
            filtered,
            key=lambda o: (urgency_order.get(o.urgency, 9), o.closing_date or date(2099, 1, 1)),
        )

        groups = {
            "critical": ("🔴 Closing in 3 days or less", [o for o in sorted_opps if o.urgency == "critical"]),
            "urgent":   ("🟠 Closing in 4–7 days",       [o for o in sorted_opps if o.urgency == "urgent"]),
            "soon":     ("🟡 Closing in 8–14 days",      [o for o in sorted_opps if o.urgency == "soon"]),
            "open":     ("🟢 Closing in 15+ days",       [o for o in sorted_opps if o.urgency == "open"]),
            "unknown":  ("⚪ Closing date TBC",           [o for o in sorted_opps if o.urgency == "unknown"]),
        }
        if show_closed:
            groups["closed"] = ("⚫ Closed", [o for o in sorted_opps if o.urgency == "closed"])

        any_shown = False
        for key, (label, items) in groups.items():
            if not items:
                continue
            any_shown = True
            st.markdown(f'<div class="section-header">{label} ({len(items)})</div>', unsafe_allow_html=True)
            if key in ("open", "unknown", "closed") and len(items) > 5:
                with st.expander(f"Show all {len(items)}", expanded=(key == "open")):
                    for o in items:
                        render_opportunity_card(o)
            else:
                for o in items:
                    render_opportunity_card(o)
        if not any_shown:
            st.info("No opportunities match your current filters.")

    # ── TAB 2: By Submission Type ─────────────────────────────────────────────
    with tab_type:
        st.markdown("Opportunities grouped by **submission type**, sorted by closing date within each group.")

        type_order = ["TENDER", "ROFP", "ROI", "EOI", "RFP", "RFQ", "PANEL", "GPN", "OTHER"]
        # Collect active types in preferred order
        active_types = [t for t in type_order if any(o.submission_type == t for o in filtered)]
        # Any types not in order list
        extra_types = [t for t in sorted(set(o.submission_type for o in filtered)) if t not in type_order]
        active_types += extra_types

        if not active_types:
            st.info("No opportunities match your current filters.")
        else:
            for sub_type in active_types:
                type_opps = [o for o in filtered if o.submission_type == sub_type]
                if not type_opps:
                    continue
                type_opps = sorted(type_opps, key=lambda o: o.closing_date or date(2099, 1, 1))
                label = SUBMISSION_TYPE_LABELS.get(sub_type, sub_type)
                colour = SUBMISSION_TYPE_COLOURS.get(sub_type, "#374151")
                st.markdown(
                    f'<div class="section-header">'
                    f'<span style="background:{colour};padding:2px 8px;border-radius:4px;font-size:0.85rem;">{sub_type}</span>'
                    f' &nbsp;{label} &nbsp;<span style="color:#64748b;font-size:0.9rem">({len(type_opps)})</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                cols_per_row = 1
                for opp in type_opps:
                    render_opportunity_card(opp, show_desc=True)

    # ── TAB 3: By Workstream ──────────────────────────────────────────────────
    with tab_workstream:
        st.markdown(
            "Opportunities matched to **Kernohan Engineering workstreams** based on keyword analysis. "
            "An opportunity may appear in multiple workstreams."
        )

        ws_list = list(WORKSTREAMS.keys())
        unmatched = [o for o in filtered if not o.workstream_tags]

        for ws_name in ws_list:
            ws_opps = [o for o in filtered if ws_name in o.workstream_tags]
            if not ws_opps:
                continue
            ws_opps = sorted(ws_opps, key=lambda o: (-o.relevance_score, o.closing_date or date(2099, 1, 1)))
            colour = WORKSTREAMS[ws_name]["colour"]
            desc = WORKSTREAMS[ws_name]["description"]
            st.markdown(
                f'<div class="section-header">'
                f'<span style="background:{colour}22;border:1px solid {colour};padding:2px 8px;border-radius:4px;font-size:0.85rem;color:{colour}">'
                f'{ws_name}</span>'
                f' &nbsp;<span style="color:#64748b;font-size:0.85rem">{desc} · {len(ws_opps)} prospects</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            with st.expander(f"Show {len(ws_opps)} opportunities", expanded=len(ws_opps) <= 3):
                for opp in ws_opps:
                    render_opportunity_card(opp)

        if unmatched:
            with st.expander(f"⚪ Unmatched ({len(unmatched)}) – no direct workstream match", expanded=False):
                for opp in unmatched:
                    render_opportunity_card(opp)

    # ── TAB 4: All Prospects ──────────────────────────────────────────────────
    with tab_all:
        sort_options = [
            "Closing Date (soonest first)",
            "Relevance Score (highest first)",
            "Submission Type",
            "Region (priority first)",
            "Agency A–Z",
        ]
        sort_by = st.selectbox("Sort by", sort_options)

        if sort_by == "Closing Date (soonest first)":
            sorted_opps = sorted(filtered, key=lambda o: o.closing_date or date(2099, 1, 1))
        elif sort_by == "Relevance Score (highest first)":
            sorted_opps = sorted(filtered, key=lambda o: -o.relevance_score)
        elif sort_by == "Submission Type":
            type_order_map = {t: i for i, t in enumerate(["TENDER", "ROFP", "ROI", "EOI", "RFP", "RFQ", "PANEL", "GPN", "OTHER"])}
            sorted_opps = sorted(filtered, key=lambda o: (type_order_map.get(o.submission_type, 9), o.closing_date or date(2099, 1, 1)))
        elif sort_by == "Region (priority first)":
            sorted_opps = sorted(filtered, key=lambda o: (not o.is_priority_region, o.region, o.closing_date or date(2099, 1, 1)))
        else:
            sorted_opps = sorted(filtered, key=lambda o: o.agency.lower())

        show_table = st.checkbox("Table view", value=False)

        if show_table and sorted_opps:
            rows = []
            for o in sorted_opps:
                rows.append({
                    "Title": o.title,
                    "Agency": o.agency,
                    "Type": o.type_label,
                    "Closing": o.closing_display,
                    "Region": o.region,
                    "Workstreams": ", ".join(o.workstream_tags) if o.workstream_tags else "—",
                    "Relevance": f"{o.relevance_score:.1f}/10",
                    "Ref": o.reference,
                    "Source": o.source.upper(),
                    "URL": o.url,
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            if not sorted_opps:
                st.info("No opportunities match your current filters.")
            for opp in sorted_opps:
                render_opportunity_card(opp, show_desc=True)

    # ── TAB 5: Export ─────────────────────────────────────────────────────────
    with tab_export:
        st.markdown("Export current filtered prospects to CSV.")

        if not filtered:
            st.info("No opportunities to export with current filters.")
        else:
            rows = []
            for o in filtered:
                rows.append({
                    "Title": o.title,
                    "Agency": o.agency,
                    "Submission Type": o.type_label,
                    "Reference": o.reference,
                    "Closing Date": o.closing_date.isoformat() if o.closing_date else "",
                    "Published Date": o.published_date.isoformat() if o.published_date else "",
                    "Closing Display": o.closing_display,
                    "Region": o.region,
                    "Priority Region": "Yes" if o.is_priority_region else "No",
                    "Workstreams": ", ".join(o.workstream_tags),
                    "Relevance Score": o.relevance_score,
                    "Category": o.category,
                    "Source": o.source,
                    "Status": o.status,
                    "URL": o.url,
                    "Description": o.description,
                })
            df = pd.DataFrame(rows)
            csv = df.to_csv(index=False)
            today_str = date.today().strftime("%Y%m%d")
            st.download_button(
                label=f"⬇️ Download {len(filtered)} opportunities as CSV",
                data=csv,
                file_name=f"kernohan_pipeline_{today_str}.csv",
                mime="text/csv",
                use_container_width=True,
            )

            st.markdown("**Preview:**")
            st.dataframe(df[["Title", "Agency", "Submission Type", "Closing Display", "Region", "Relevance Score"]]
                         .head(20), use_container_width=True, hide_index=True)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.divider()
    st.caption(
        "Kernohan Engineering Sales Pipeline · Nelson, NZ · "
        "Data sourced from GETS (Government Electronic Tender Service), Nelson City Council, "
        "Tasman District Council, Marlborough District Council, and Port Nelson. "
        "Auto-refreshes every Monday at 4:00 pm NZST. "
        "Always verify opportunity details directly with the issuing agency."
    )

    # ── Background scheduler trigger ──────────────────────────────────────────
    _check_scheduled_scrape()


def _check_scheduled_scrape() -> None:
    """
    Check if a scheduled Monday 4pm scrape is due and run it automatically.
    Uses Streamlit session state to avoid running more than once per session/hour.
    """
    now = datetime.now(tz=NZT)
    is_monday = now.weekday() == 0
    is_after_4pm = now.hour >= 16
    is_before_5pm = now.hour < 17  # 1-hour window

    if not (is_monday and is_after_4pm and is_before_5pm):
        return

    # Check session state to avoid multiple runs in the same hour
    last_auto = st.session_state.get("last_auto_scrape_hour")
    current_hour_key = now.strftime("%Y-%m-%d-%H")
    if last_auto == current_hour_key:
        return

    # Mark as done for this hour
    st.session_state["last_auto_scrape_hour"] = current_hour_key

    with st.spinner("🔄 Scheduled Monday refresh running…"):
        status = st.empty()
        count, mode = do_scrape(status)
        if mode == "live":
            st.toast(f"✅ Weekly refresh complete — {count} opportunities updated.")
        else:
            st.toast(f"⚠️ Weekly refresh used demo data ({count} opportunities).")
    st.rerun()


if __name__ == "__main__":
    main()
