"""
SQLite database for caching scraped property listings.
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from models import PropertyListing

DB_PATH = Path(__file__).parent / "properties.db"


def init_db():
    """Create the database and tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id TEXT PRIMARY KEY,
            source TEXT,
            title TEXT,
            address TEXT,
            region TEXT,
            url TEXT,
            price REAL,
            price_display TEXT,
            annual_rent REAL,
            yield_pct REAL,
            yield_display TEXT,
            floor_area REAL,
            land_area REAL,
            site_coverage REAL,
            property_type TEXT,
            zoning TEXT,
            description TEXT,
            features TEXT,
            is_bare_land INTEGER,
            is_leased INTEGER,
            lease_expiry TEXT,
            dev_score REAL,
            dev_notes TEXT,
            image_url TEXT,
            listed_date TEXT,
            agent TEXT,
            scraped_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scrape_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            started_at TEXT,
            finished_at TEXT,
            count INTEGER,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_listings(listings: list[PropertyListing]):
    """Insert or replace a list of listings."""
    if not listings:
        return
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now().isoformat()
    for listing in listings:
        d = listing.to_dict()
        d["scraped_at"] = now
        conn.execute("""
            INSERT OR REPLACE INTO listings VALUES (
                :id, :source, :title, :address, :region, :url,
                :price, :price_display, :annual_rent, :yield_pct, :yield_display,
                :floor_area, :land_area, :site_coverage,
                :property_type, :zoning, :description, :features,
                :is_bare_land, :is_leased, :lease_expiry,
                :dev_score, :dev_notes, :image_url, :listed_date, :agent, :scraped_at
            )
        """, d)
    conn.commit()
    conn.close()


def load_listings(source: str = None) -> list[PropertyListing]:
    """Load all listings, optionally filtered by source."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if source:
        rows = conn.execute(
            "SELECT * FROM listings WHERE source = ? ORDER BY yield_pct DESC NULLS LAST",
            (source,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM listings ORDER BY yield_pct DESC NULLS LAST"
        ).fetchall()
    conn.close()
    return [PropertyListing.from_dict(dict(row)) for row in rows]


def get_last_scrape_time() -> str:
    """Return the most recent scrape timestamp."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT MAX(scraped_at) FROM listings"
    ).fetchone()
    conn.close()
    if row and row[0]:
        dt = datetime.fromisoformat(row[0])
        return dt.strftime("%d %b %Y %H:%M")
    return "Never"


def count_listings() -> int:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT COUNT(*) FROM listings").fetchone()
    conn.close()
    return row[0] if row else 0


def clear_listings(source: str = None):
    """Remove listings, optionally only from a specific source."""
    conn = sqlite3.connect(DB_PATH)
    if source:
        conn.execute("DELETE FROM listings WHERE source = ?", (source,))
    else:
        conn.execute("DELETE FROM listings")
    conn.commit()
    conn.close()
