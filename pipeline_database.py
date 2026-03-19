"""
SQLite database layer for the Kernohan Engineering Sales Pipeline.
"""
from __future__ import annotations
import sqlite3
import json
import hashlib
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from pipeline_models import Opportunity, score_opportunity

DB_PATH = Path(__file__).parent / "pipeline.db"

# ── Schema ────────────────────────────────────────────────────────────────────

DDL = """
CREATE TABLE IF NOT EXISTS opportunities (
    id               TEXT PRIMARY KEY,
    title            TEXT NOT NULL,
    agency           TEXT NOT NULL,
    submission_type  TEXT NOT NULL,
    closing_date     TEXT,
    published_date   TEXT,
    region           TEXT,
    url              TEXT,
    description      TEXT,
    reference        TEXT,
    source           TEXT,
    category         TEXT,
    workstream_tags  TEXT,   -- JSON list
    relevance_score  REAL,
    status           TEXT,
    last_seen        TEXT
);

CREATE TABLE IF NOT EXISTS scrape_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    scraped_at  TEXT NOT NULL,
    source      TEXT,
    count       INTEGER,
    notes       TEXT
);
"""


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        for stmt in DDL.strip().split(";"):
            s = stmt.strip()
            if s:
                conn.execute(s)
        conn.commit()


# ── Persistence helpers ───────────────────────────────────────────────────────

def _date_str(d: Optional[date]) -> Optional[str]:
    return d.isoformat() if d else None


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def make_id(title: str, agency: str, source: str) -> str:
    raw = f"{title.strip().lower()}|{agency.strip().lower()}|{source}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


# ── CRUD ──────────────────────────────────────────────────────────────────────

def save_opportunities(opps: list[Opportunity]) -> int:
    """Upsert opportunities; return count saved."""
    init_db()
    if not opps:
        return 0

    rows = []
    for o in opps:
        score, tags = score_opportunity(o)
        o.relevance_score = score
        o.workstream_tags = tags
        o.last_seen = datetime.utcnow()
        rows.append((
            o.id,
            o.title,
            o.agency,
            o.submission_type,
            _date_str(o.closing_date),
            _date_str(o.published_date),
            o.region,
            o.url,
            o.description,
            o.reference,
            o.source,
            o.category,
            json.dumps(o.workstream_tags),
            o.relevance_score,
            o.status,
            o.last_seen.isoformat(),
        ))

    with _conn() as conn:
        conn.executemany(
            """
            INSERT INTO opportunities
              (id, title, agency, submission_type, closing_date, published_date,
               region, url, description, reference, source, category,
               workstream_tags, relevance_score, status, last_seen)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
              title           = excluded.title,
              agency          = excluded.agency,
              submission_type = excluded.submission_type,
              closing_date    = excluded.closing_date,
              published_date  = excluded.published_date,
              region          = excluded.region,
              url             = excluded.url,
              description     = excluded.description,
              reference       = excluded.reference,
              source          = excluded.source,
              category        = excluded.category,
              workstream_tags = excluded.workstream_tags,
              relevance_score = excluded.relevance_score,
              status          = excluded.status,
              last_seen       = excluded.last_seen
            """,
            rows,
        )
        conn.commit()

    return len(rows)


def load_opportunities(
    include_closed: bool = False,
    source_filter: Optional[list[str]] = None,
) -> list[Opportunity]:
    init_db()
    with _conn() as conn:
        query = "SELECT * FROM opportunities"
        params: list = []
        conditions = []
        if not include_closed:
            conditions.append("(closing_date IS NULL OR closing_date >= date('now', '-1 day'))")
        if source_filter:
            placeholders = ",".join("?" * len(source_filter))
            conditions.append(f"source IN ({placeholders})")
            params.extend(source_filter)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY closing_date ASC NULLS LAST"
        rows = conn.execute(query, params).fetchall()

    result = []
    for r in rows:
        opp = Opportunity(
            id=r["id"],
            title=r["title"],
            agency=r["agency"],
            submission_type=r["submission_type"],
            closing_date=_parse_date(r["closing_date"]),
            published_date=_parse_date(r["published_date"]),
            region=r["region"] or "Unknown",
            url=r["url"] or "",
            description=r["description"] or "",
            reference=r["reference"] or "",
            source=r["source"] or "",
            category=r["category"] or "",
            workstream_tags=json.loads(r["workstream_tags"] or "[]"),
            relevance_score=r["relevance_score"] or 0.0,
            status=r["status"] or "open",
            last_seen=_parse_dt(r["last_seen"]),
        )
        result.append(opp)
    return result


def log_scrape(source: str, count: int, notes: str = "") -> None:
    init_db()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO scrape_log (scraped_at, source, count, notes) VALUES (?,?,?,?)",
            (datetime.utcnow().isoformat(), source, count, notes),
        )
        conn.commit()


def get_last_scrape_time() -> Optional[str]:
    init_db()
    with _conn() as conn:
        row = conn.execute(
            "SELECT scraped_at FROM scrape_log ORDER BY scraped_at DESC LIMIT 1"
        ).fetchone()
    if not row:
        return None
    try:
        dt = datetime.fromisoformat(row["scraped_at"])
        return dt.strftime("%-d %b %Y %H:%M UTC")
    except Exception:
        return row["scraped_at"]


def count_opportunities() -> int:
    init_db()
    with _conn() as conn:
        row = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()
    return row[0] if row else 0


def mark_closed(opp_id: str) -> None:
    with _conn() as conn:
        conn.execute("UPDATE opportunities SET status='closed' WHERE id=?", (opp_id,))
        conn.commit()


def clear_all() -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM opportunities")
        conn.commit()
