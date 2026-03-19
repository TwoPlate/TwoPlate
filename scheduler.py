"""
Kernohan Engineering Sales Pipeline – Scheduled Refresh
========================================================
Standalone scheduler that runs the pipeline scraper every Monday at 4:00 pm NZST.
Can be run as a background service alongside the Streamlit app, or as a cron job.

Usage (background service):
    python scheduler.py

Usage (cron – add to crontab):
    # Run every Monday at 4pm NZT (UTC+12 / UTC+13 with DST)
    # NZT 4pm = UTC 4am (NZST) or UTC 3am (NZDT)
    # Use CRON_TZ if your cron supports it, or adjust UTC offset manually:
    0 4 * * 1 cd /path/to/TwoPlate && python scheduler.py --once

    # Or with CRON_TZ:
    CRON_TZ=Pacific/Auckland
    0 16 * * 1 cd /path/to/TwoPlate && python scheduler.py --once

Usage (manual one-off run):
    python scheduler.py --once
"""
from __future__ import annotations
import asyncio
import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path(__file__).parent / "pipeline_scheduler.log"),
    ],
)
logger = logging.getLogger("scheduler")

NZT = ZoneInfo("Pacific/Auckland")

# ── Scrape job ────────────────────────────────────────────────────────────────

async def _run_scrapers() -> tuple[int, str]:
    """Run all scrapers and save results. Returns (count, mode)."""
    from pipeline_scrapers import ALL_SCRAPERS
    from pipeline_database import save_opportunities, log_scrape

    all_opps = []
    for ScraperClass in ALL_SCRAPERS:
        scraper = ScraperClass()
        try:
            logger.info("Scraping: %s", scraper.display_name)
            opps = await scraper.scrape(
                progress_callback=lambda msg, n=scraper.display_name: logger.info("[%s] %s", n, msg)
            )
            all_opps.extend(opps)
            logger.info("%s complete – %d opportunities found", scraper.display_name, len(opps))
        except Exception as exc:
            logger.error("%s failed: %s", scraper.display_name, exc, exc_info=True)

    if all_opps:
        saved = save_opportunities(all_opps)
        log_scrape("all", saved)
        logger.info("Saved %d opportunities to database.", saved)
        return saved, "live"

    # Fallback to demo
    logger.warning("All scrapers returned empty results. Loading demo data as fallback.")
    from pipeline_scrapers.demo import get_demo_opportunities
    demo_opps = get_demo_opportunities()
    saved = save_opportunities(demo_opps)
    log_scrape("demo", saved, "all scrapers empty – demo fallback")
    logger.info("Demo data loaded: %d opportunities.", saved)
    return saved, "demo"


def run_scrape_job() -> None:
    """Synchronous wrapper for the scrape job (called by APScheduler)."""
    now_nzt = datetime.now(tz=NZT)
    logger.info("=" * 60)
    logger.info("Scheduled scrape starting – %s NZT", now_nzt.strftime("%A %-d %b %Y %H:%M"))
    logger.info("=" * 60)
    try:
        count, mode = asyncio.run(_run_scrapers())
        logger.info("Scrape complete. Mode=%s, Saved=%d", mode, count)
    except Exception as exc:
        logger.error("Scrape job failed: %s", exc, exc_info=True)


# ── Scheduler setup ───────────────────────────────────────────────────────────

def start_scheduler() -> None:
    """Start APScheduler – runs every Monday at 16:00 NZT."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error("APScheduler not installed. Run: pip install apscheduler")
        sys.exit(1)

    scheduler = BlockingScheduler(timezone=NZT)
    trigger = CronTrigger(
        day_of_week="mon",
        hour=16,
        minute=0,
        timezone=NZT,
    )
    scheduler.add_job(
        run_scrape_job,
        trigger=trigger,
        id="monday_pipeline_refresh",
        name="Kernohan Pipeline – Monday 4pm Refresh",
        replace_existing=True,
        misfire_grace_time=3600,   # allow up to 1hr late if system was off
    )

    next_run = scheduler.get_jobs()[0].next_run_time
    logger.info("Scheduler started.")
    logger.info("Next run: %s NZT", next_run.strftime("%-d %b %Y at %H:%M") if next_run else "Unknown")
    logger.info("Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--once" in sys.argv:
        # Single run (useful for cron)
        logger.info("Running single scrape job (--once mode).")
        run_scrape_job()
    else:
        # Persistent background scheduler
        start_scheduler()
