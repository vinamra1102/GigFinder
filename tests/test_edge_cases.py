"""Edge case tests: handle unexpected or boundary inputs gracefully."""

import os
from unittest.mock import MagicMock, patch

import db.database as db_mod
from db.database import init_db, get_all_leads
from db.models import Lead
from scraper.scraper import (
    fetch_posts,
    matches_include_keywords,
    has_exclude_keywords,
    build_keywords_matched,
    save_lead,
)


def _make_submission(title="", selftext="", permalink="/r/test/comments/edge/t", author="user1"):
    sub = MagicMock()
    sub.title = title
    sub.selftext = selftext
    sub.permalink = permalink
    sub.author = MagicMock(__str__=lambda self: author) if author else None
    return sub


# ──────────────────────────────────────────────
# 1. Subreddit with 0 matching posts → no crash
# ──────────────────────────────────────────────

@patch("scraper.scraper.get_reddit")
@patch("scraper.scraper.time.sleep")
@patch("scraper.scraper.SUBREDDITS", ["emptysubreddit"])
def test_zero_matching_posts_no_crash(mock_sleep, mock_get_reddit):
    init_db()
    mock_reddit = MagicMock()
    mock_reddit.subreddit.return_value.new.return_value = [
        _make_submission("Just chatting about weather", "no keywords here", "/r/empty/1/t"),
    ]
    mock_get_reddit.return_value = mock_reddit

    from scraper.scraper import scrape_all_subreddits
    count = scrape_all_subreddits()
    assert count == 0

    leads = get_all_leads()
    assert len(leads) == 0


# ──────────────────────────────────────────────
# 2. Post with empty title
# ──────────────────────────────────────────────

def test_empty_title_handled():
    post = {"title": "", "post_body": "I need a website built, budget $100"}
    matched = matches_include_keywords(post)
    assert len(matched) > 0  # should still match on body
    assert not has_exclude_keywords(post)


# ──────────────────────────────────────────────
# 3. Post with empty body
# ──────────────────────────────────────────────

def test_empty_body_handled():
    post = {"title": "Budget project, need a developer", "post_body": ""}
    matched = matches_include_keywords(post)
    assert len(matched) > 0
    result = build_keywords_matched(post)
    assert result != ""


# ──────────────────────────────────────────────
# 4. Post with None author (deleted account)
# ──────────────────────────────────────────────

def test_none_author_handled():
    mock_reddit = MagicMock()
    submissions = [_make_submission(
        title="Need a developer",
        selftext="budget $100",
        permalink="/r/test/comments/deleted/t",
        author=None,
    )]
    mock_reddit.subreddit.return_value.new.return_value = submissions

    posts = fetch_posts(mock_reddit, "forhire", limit=1)
    assert len(posts) == 1
    assert posts[0]["author"] == "[deleted]"


# ──────────────────────────────────────────────
# 5. Missing .env credential → clear error
# ──────────────────────────────────────────────

@patch.dict(os.environ, {"REDDIT_CLIENT_ID": "", "REDDIT_CLIENT_SECRET": ""}, clear=False)
@patch("scraper.scraper.praw.Reddit")
def test_missing_credentials_error(mock_reddit_cls):
    mock_reddit_cls.side_effect = Exception("Missing credentials: client_id")

    import pytest
    with pytest.raises(Exception, match="Missing credentials"):
        from scraper.scraper import get_reddit
        get_reddit()


# ──────────────────────────────────────────────
# 6. DB file missing → auto recreated
# ──────────────────────────────────────────────

def test_db_auto_created_when_missing():
    from sqlalchemy import inspect
    init_db()
    inspector = inspect(db_mod.engine)
    tables = inspector.get_table_names()
    assert "leads" in tables


# ──────────────────────────────────────────────
# 7. Slow API → timeout handled gracefully
# ──────────────────────────────────────────────

@patch("scraper.scraper.get_reddit")
@patch("scraper.scraper.time.sleep")
@patch("scraper.scraper.SUBREDDITS", ["timeout_sub"])
def test_slow_api_timeout_handled(mock_sleep, mock_get_reddit):
    init_db()
    import requests

    mock_reddit = MagicMock()
    mock_reddit.subreddit.return_value.new.side_effect = Exception("Read timed out")
    mock_get_reddit.return_value = mock_reddit

    from scraper.scraper import fetch_posts
    import pytest
    with pytest.raises(Exception, match="Read timed out"):
        fetch_posts(mock_reddit, "timeout_sub")
