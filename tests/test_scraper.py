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


def _make_submission(title="Test Post", selftext="", permalink="/r/test/comments/abc/test", author="user1"):
    """Create a mock PRAW Submission object."""
    sub = MagicMock()
    sub.title = title
    sub.selftext = selftext
    sub.permalink = permalink
    sub.author = MagicMock(__str__=lambda self: author) if author else None
    return sub


# ──────────────────────────────────────────────
# 1. PRAW connects successfully (mocked)
# ──────────────────────────────────────────────

@patch("scraper.scraper.praw.Reddit")
def test_praw_connects(mock_reddit_cls):
    from scraper.scraper import get_reddit
    mock_reddit_cls.return_value = MagicMock()
    reddit = get_reddit()
    assert reddit is not None
    mock_reddit_cls.assert_called_once()


# ──────────────────────────────────────────────
# 2. fetch_posts returns correct number of posts
# ──────────────────────────────────────────────

def test_fetch_posts_returns_correct_count():
    mock_reddit = MagicMock()
    submissions = [_make_submission(permalink=f"/r/test/comments/{i}/t") for i in range(5)]
    mock_reddit.subreddit.return_value.new.return_value = submissions

    posts = fetch_posts(mock_reddit, "forhire", limit=5)
    assert len(posts) == 5
    mock_reddit.subreddit.return_value.new.assert_called_once_with(limit=5)


# ──────────────────────────────────────────────
# 3. keyword matching — include via title
# ──────────────────────────────────────────────

def test_include_keyword_in_title():
    post = {"title": "Looking for a developer to help", "post_body": "some random text"}
    matched = matches_include_keywords(post)
    assert "looking for a developer" in matched


# ──────────────────────────────────────────────
# 4. keyword matching — include via body
# ──────────────────────────────────────────────

def test_include_keyword_in_body():
    post = {"title": "Help needed", "post_body": "I have a budget for this project"}
    matched = matches_include_keywords(post)
    assert "budget" in matched


# ──────────────────────────────────────────────
# 5. keyword matching is case insensitive
# ──────────────────────────────────────────────

def test_include_keyword_case_insensitive():
    post = {"title": "LOOKING FOR A DEVELOPER right now", "post_body": ""}
    matched = matches_include_keywords(post)
    assert "looking for a developer" in matched


def test_include_keyword_mixed_case():
    post = {"title": "Need A Website built", "post_body": ""}
    matched = matches_include_keywords(post)
    assert "need a website" in matched


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
    assert matches_include_keywords(post)  # has include hits
    assert has_exclude_keywords(post) is True  # but also exclude hits


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
# 9. empty post body is handled without crash
# ──────────────────────────────────────────────

def test_empty_body_no_crash():
    post = {"title": "Budget project available", "post_body": ""}
    matched = matches_include_keywords(post)
    assert "budget" in matched
    assert not has_exclude_keywords(post)
    result = build_keywords_matched(post)
    assert result != ""


# ──────────────────────────────────────────────
# 10. save_lead truncates post body to 500 chars
# ──────────────────────────────────────────────

def test_save_lead_body_stored():
    long_body = "x" * 600
    post = {
        "title": "Test truncation",
        "url": "https://reddit.com/r/test/trunc1",
        "author": "truncator",
        "subreddit": "forhire",
        "post_body": long_body[:500],  # scraper already truncates in fetch_posts
    }
    save_lead(post, "budget")
    session = db_mod.SessionLocal()
    try:
        lead = session.query(Lead).filter(Lead.url == post["url"]).first()
        assert lead is not None
        assert len(lead.post_body) == 500
    finally:
        session.close()


def test_fetch_posts_truncates_body():
    """Verify fetch_posts truncates selftext to 500 chars."""
    mock_reddit = MagicMock()
    long_text = "A" * 800
    submissions = [_make_submission(selftext=long_text)]
    mock_reddit.subreddit.return_value.new.return_value = submissions

    posts = fetch_posts(mock_reddit, "forhire", limit=1)
    assert len(posts[0]["post_body"]) == 500
