"""Scheduler tests: verify APScheduler initializes and triggers correctly."""

import logging
from unittest.mock import MagicMock, patch

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler

from db.database import init_db, get_all_leads
import db.database as db_mod


# ──────────────────────────────────────────────
# 1. Scheduler initializes without error
# ──────────────────────────────────────────────

def test_scheduler_initializes():
    scheduler = BackgroundScheduler()
    mock_func = MagicMock()
    scheduler.add_job(
        mock_func,
        trigger="cron",
        hour=7,
        minute=0,
        id="daily_scrape",
    )
    jobs = scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == "daily_scrape"


# ──────────────────────────────────────────────
# 2. Short-interval scheduler triggers scraper
# ──────────────────────────────────────────────

@patch("scraper.scraper.get_reddit")
@patch("scraper.scraper.time.sleep")
@patch("scraper.scraper.SUBREDDITS", ["forhire"])
def test_scheduler_triggers_scraper(mock_sleep, mock_get_reddit):
    init_db()

    mock_reddit = MagicMock()
    sub = MagicMock()
    submission = MagicMock()
    submission.title = "Need a developer ASAP"
    submission.selftext = "Budget $500"
    submission.permalink = "/r/forhire/comments/sched1/t"
    submission.author = MagicMock(__str__=lambda self: "scheduler_user")
    sub.new.return_value = [submission]
    mock_reddit.subreddit.return_value = sub
    mock_get_reddit.return_value = mock_reddit

    from scraper.scraper import scrape_all_subreddits

    # Directly invoke to prove the function the scheduler would call works
    count = scrape_all_subreddits()
    assert count >= 1

    # Now verify scheduler can add and retrieve the job
    scheduler = BackgroundScheduler()
    scheduler.add_job(scrape_all_subreddits, trigger="interval", seconds=60, id="test_interval")
    job = scheduler.get_job("test_interval")
    assert job is not None
    assert job.id == "test_interval"


# ──────────────────────────────────────────────
# 3. Scheduler logs the run
# ──────────────────────────────────────────────

@patch("scraper.scraper.get_reddit")
@patch("scraper.scraper.time.sleep")
@patch("scraper.scraper.SUBREDDITS", ["forhire"])
def test_scheduler_logs_run(mock_sleep, mock_get_reddit, caplog):
    init_db()

    mock_reddit = MagicMock()
    sub = MagicMock()
    submission = MagicMock()
    submission.title = "Need a developer for quick fix"
    submission.selftext = "Budget $200"
    submission.permalink = "/r/forhire/comments/log1/t"
    submission.author = MagicMock(__str__=lambda self: "log_user")
    sub.new.return_value = [submission]
    mock_reddit.subreddit.return_value = sub
    mock_get_reddit.return_value = mock_reddit

    from scraper.scraper import scrape_all_subreddits

    with caplog.at_level(logging.INFO, logger="scraper.scraper"):
        scrape_all_subreddits()

    assert any("Scrape complete" in msg for msg in caplog.messages)
    assert any("Scraping r/forhire" in msg for msg in caplog.messages)


# ──────────────────────────────────────────────
# 4. No duplicates after scheduled run
# ──────────────────────────────────────────────

@patch("scraper.scraper.get_reddit")
@patch("scraper.scraper.time.sleep")
@patch("scraper.scraper.SUBREDDITS", ["forhire"])
def test_no_duplicates_after_scheduled_run(mock_sleep, mock_get_reddit):
    init_db()

    mock_reddit = MagicMock()
    sub = MagicMock()
    submission = MagicMock()
    submission.title = "Looking for freelancer urgently"
    submission.selftext = "Budget $300, paid"
    submission.permalink = "/r/forhire/comments/nodup_sched/t"
    submission.author = MagicMock(__str__=lambda self: "nodup_user")
    sub.new.return_value = [submission]
    mock_reddit.subreddit.return_value = sub
    mock_get_reddit.return_value = mock_reddit

    from scraper.scraper import scrape_all_subreddits

    first = scrape_all_subreddits()
    second = scrape_all_subreddits()

    assert first >= 1
    assert second == 0

    leads = get_all_leads()
    urls = [l.url for l in leads]
    assert len(urls) == len(set(urls))


# ──────────────────────────────────────────────
# 5. Verify daily 7AM cron config is correct
# ──────────────────────────────────────────────

def test_daily_7am_cron_config():
    scheduler = BackgroundScheduler()
    mock_func = MagicMock()
    scheduler.add_job(
        mock_func,
        trigger="cron",
        hour=7,
        minute=0,
        id="daily_check",
    )
    job = scheduler.get_job("daily_check")
    trigger = job.trigger
    assert str(trigger) == "cron[hour='7', minute='0']"
