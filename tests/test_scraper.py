import json
from unittest.mock import MagicMock, patch

from scraper.scraper import (
    fetch_posts,
    matches_include_keywords,
    has_exclude_keywords,
    build_keywords_matched,
    save_lead,
    url_exists,
)
import db.database as db_mod
from db.models import Lead


def _make_response(posts):
    """Build a mock requests.Response returning Reddit JSON for given post dicts."""
    children = [{"data": p} for p in posts]
    payload = {"data": {"children": children}}
    mock_resp = MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status.return_value = None
    return mock_resp


def _post_data(title="Test Post", selftext="", permalink="/r/test/comments/abc/test", author="user1"):
    return {
        "title": title,
        "selftext": selftext,
        "permalink": permalink,
        "author": author,
    }


# ──────────────────────────────────────────────
# 1. fetch_posts returns correct number of posts
# ──────────────────────────────────────────────

@patch("scraper.scraper.SESSION")
def test_fetch_posts_returns_correct_count(mock_session):
    mock_session.get.return_value = _make_response([
        _post_data(permalink=f"/r/test/comments/{i}/t") for i in range(5)
    ])
    posts = fetch_posts("forhire", limit=5)
    assert len(posts) == 5


# ──────────────────────────────────────────────
# 2. HTTP error returns empty list (no crash)
# ──────────────────────────────────────────────

@patch("scraper.scraper.SESSION")
def test_fetch_posts_http_error_returns_empty(mock_session):
    import requests as req
    mock_session.get.side_effect = req.RequestException("timeout")
    posts = fetch_posts("forhire", limit=5)
    assert posts == []


# ──────────────────────────────────────────────
# 3. keyword matching — include via title
# ──────────────────────────────────────────────

def test_include_keyword_in_title():
    post = {"title": "Looking for a developer to help", "post_body": "some random text"}
    assert "looking for a developer" in matches_include_keywords(post)


# ──────────────────────────────────────────────
# 4. keyword matching — include via body
# ──────────────────────────────────────────────

def test_include_keyword_in_body():
    post = {"title": "Help needed", "post_body": "I have a budget for this project"}
    assert "budget" in matches_include_keywords(post)


# ──────────────────────────────────────────────
# 5. keyword matching is case insensitive
# ──────────────────────────────────────────────

def test_include_keyword_case_insensitive():
    post = {"title": "LOOKING FOR A DEVELOPER right now", "post_body": ""}
    assert "looking for a developer" in matches_include_keywords(post)


def test_include_keyword_mixed_case():
    post = {"title": "Need A Website built", "post_body": ""}
    assert "need a website" in matches_include_keywords(post)


# ──────────────────────────────────────────────
# 6. exclude keywords correctly filter
# ──────────────────────────────────────────────

def test_exclude_keyword_in_title(sample_post_exclude):
    assert has_exclude_keywords(sample_post_exclude) is True


def test_exclude_keyword_equity():
    post = {"title": "Looking for someone", "post_body": "offering equity in startup"}
    assert has_exclude_keywords(post) is True


def test_no_exclude_keyword():
    post = {"title": "Need a quick fix", "post_body": "budget $200"}
    assert has_exclude_keywords(post) is False


# ──────────────────────────────────────────────
# 7. post with both include and exclude → excluded
# ──────────────────────────────────────────────

def test_post_with_include_and_exclude():
    post = {
        "title": "Looking for a developer, co-founder role",
        "post_body": "equity split 50/50",
    }
    assert matches_include_keywords(post)
    assert has_exclude_keywords(post) is True


# ──────────────────────────────────────────────
# 8. keywords_matched lists all matches
# ──────────────────────────────────────────────

def test_keywords_matched_lists_all():
    post = {"title": "Need a website, budget $500", "post_body": "ASAP please, quick fix needed"}
    result = build_keywords_matched(post)
    assert "budget" in result
    assert "need a website" in result
    assert "asap" in result
    assert "quick fix" in result


# ──────────────────────────────────────────────
# 9. empty post body handled without crash
# ──────────────────────────────────────────────

def test_empty_body_no_crash():
    post = {"title": "Budget project available", "post_body": ""}
    assert "budget" in matches_include_keywords(post)
    assert not has_exclude_keywords(post)
    assert build_keywords_matched(post) != ""


# ──────────────────────────────────────────────
# 10. fetch_posts truncates selftext to 500 chars
# ──────────────────────────────────────────────

@patch("scraper.scraper.SESSION")
def test_fetch_posts_truncates_body(mock_session):
    long_text = "A" * 800
    mock_session.get.return_value = _make_response([
        _post_data(selftext=long_text, permalink="/r/test/comments/trunc/t")
    ])
    posts = fetch_posts("forhire", limit=1)
    assert len(posts[0]["post_body"]) == 500


# ──────────────────────────────────────────────
# 11. save_lead stores post body correctly
# ──────────────────────────────────────────────

def test_save_lead_body_stored():
    post = {
        "title": "Test truncation",
        "url": "https://reddit.com/r/test/trunc1",
        "author": "truncator",
        "subreddit": "forhire",
        "post_body": "x" * 500,
    }
    save_lead(post, "budget")
    session = db_mod.SessionLocal()
    try:
        lead = session.query(Lead).filter(Lead.url == post["url"]).first()
        assert lead is not None
        assert len(lead.post_body) == 500
    finally:
        session.close()


# ──────────────────────────────────────────────
# 12. None author falls back to [deleted]
# ──────────────────────────────────────────────

@patch("scraper.scraper.SESSION")
def test_none_author_becomes_deleted(mock_session):
    mock_session.get.return_value = _make_response([
        _post_data(author=None, permalink="/r/test/comments/noauth/t")
    ])
    posts = fetch_posts("forhire", limit=1)
    assert posts[0]["author"] == "[deleted]"
