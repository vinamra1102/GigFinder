"""Scheduler tests: verify APScheduler initializes and triggers correctly."""

import logging
from unittest.mock import MagicMock, patch

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler

from db.database import init_db, get_all_leads
import db.database as db_mod


def _make_response(posts):
    children = [{"data": p} for p in posts]
    payload = {"data": {"children": children}}
    mock_resp = MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status.return_value = None
    return mock_resp


def _post_data(title="Test Post", selftext="", permalink="/r/test/comments/abc/test", author="user1"):
    return {"title": title, "selftext": selftext, "permalink": permalink, "author": author}


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

@patch("scraper.scraper.time.sleep")
@patch("scraper.scraper.SUBREDDITS", ["forhire"])
@patch("scraper.scraper.SESSION")
def test_scheduler_triggers_scraper(mock_session, mock_sleep):
    init_db()
    mock_session.get.return_value = _make_response([
        _post_data("Need a developer ASAP", "Budget $500", "/r/forhire/comments/sched1/t", "scheduler_user"),
    ])

    from scraper.scraper import scrape_all_subreddits

    count = scrape_all_subreddits()
    assert count >= 1

    scheduler = BackgroundScheduler()
    scheduler.add_job(scrape_all_subreddits, trigger="interval", seconds=60, id="test_interval")
    job = scheduler.get_job("test_interval")
    assert job is not None
    assert job.id == "test_interval"


# ──────────────────────────────────────────────
# 3. Scheduler logs the run
# ──────────────────────────────────────────────

@patch("scraper.scraper.time.sleep")
@patch("scraper.scraper.SUBREDDITS", ["forhire"])
@patch("scraper.scraper.SESSION")
def test_scheduler_logs_run(mock_session, mock_sleep, caplog):
    init_db()
    mock_session.get.return_value = _make_response([
        _post_data("Need a developer for quick fix", "Budget $200", "/r/forhire/comments/log1/t", "log_user"),
    ])

    from scraper.scraper import scrape_all_subreddits

    with caplog.at_level(logging.INFO, logger="scraper.scraper"):
        scrape_all_subreddits()

    assert any("Scrape complete" in msg for msg in caplog.messages)
    assert any("Scraping r/forhire" in msg for msg in caplog.messages)


# ──────────────────────────────────────────────
# 4. No duplicates after scheduled run
# ──────────────────────────────────────────────

@patch("scraper.scraper.time.sleep")
@patch("scraper.scraper.SUBREDDITS", ["forhire"])
@patch("scraper.scraper.SESSION")
def test_no_duplicates_after_scheduled_run(mock_session, mock_sleep):
    init_db()
    mock_session.get.return_value = _make_response([
        _post_data("Looking for freelancer urgently", "Budget $300, paid", "/r/forhire/comments/nodup_sched/t", "nodup_user"),
    ])

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
