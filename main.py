# GigFinder — entry point
# Usage:
#   python main.py            → run scraper once manually
#   python main.py --schedule → run scraper on daily schedule (7 AM)

import argparse


def run_scraper():
    # Will be wired to scraper.scrape_all_subreddits() in Phase 3
    pass


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
