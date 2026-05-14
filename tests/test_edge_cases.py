"""Edge case tests: handle unexpected or boundary inputs gracefully."""

import os
from unittest.mock import MagicMock, patch

import requests as req

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


def _make_response(posts):
    children = [{"data": p} for p in posts]
    payload = {"data": {"children": children}}
    mock_resp = MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status.return_value = None
    return mock_resp


def _post_data(title="", selftext="", permalink="/r/test/comments/edge/t", author="user1"):
    return {"title": title, "selftext": selftext, "permalink": permalink, "author": author}


# ──────────────────────────────────────────────
# 1. Subreddit with 0 matching posts → no crash
# ──────────────────────────────────────────────

@patch("scraper.scraper.time.sleep")
@patch("scraper.scraper.SUBREDDITS", ["emptysubreddit"])
@patch("scraper.scraper.SESSION")
def test_zero_matching_posts_no_crash(mock_session, mock_sleep):
    init_db()
    mock_session.get.return_value = _make_response([
        _post_data("Just chatting about weather", "no keywords here", "/r/empty/1/t"),
    ])
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
    assert len(matched) > 0
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

@patch("scraper.scraper.SESSION")
def test_none_author_handled(mock_session):
    mock_session.get.return_value = _make_response([
        _post_data("Need a developer", "budget $100", "/r/test/comments/deleted/t", author=None),
    ])
    posts = fetch_posts("forhire", limit=1)
    assert len(posts) == 1
    assert posts[0]["author"] == "[deleted]"


# ──────────────────────────────────────────────
# 5. HTTP 429 rate-limit → returns empty list
# ──────────────────────────────────────────────

@patch("scraper.scraper.SESSION")
def test_rate_limit_returns_empty(mock_session):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = req.HTTPError("429 Too Many Requests")
    mock_session.get.return_value = mock_resp
    posts = fetch_posts("forhire", limit=5)
    assert posts == []


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
# 7. Network timeout → returns empty list
# ──────────────────────────────────────────────

@patch("scraper.scraper.SESSION")
def test_network_timeout_returns_empty(mock_session):
    mock_session.get.side_effect = req.Timeout("Read timed out")
    posts = fetch_posts("forhire", limit=5)
    assert posts == []
