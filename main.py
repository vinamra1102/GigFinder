# GigFinder — entry point
# Usage:
#   python main.py            → run scraper once manually
#   python main.py --schedule → run scraper on daily schedule (7 AM)

import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

from db.database import init_db
from scraper.scraper import scrape_all_subreddits


def run_scraper():
    init_db()
    count = scrape_all_subreddits()
    print(f"Done — {count} new lead(s) saved.")


def run_scheduler():
    # Will be wired to APScheduler in Phase 4
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GigFinder Reddit Lead Scraper")
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run on a daily schedule instead of a one-shot scrape",
    )
    args = parser.parse_args()

    if args.schedule:
        run_scheduler()
    else:
        run_scraper()
