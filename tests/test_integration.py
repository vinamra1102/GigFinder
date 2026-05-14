"""Integration tests: exercise the full scraper → DB pipeline with mocked PRAW."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import db.database as db_mod
from db.database import get_all_leads, init_db, update_lead_status
from db.models import Lead, LeadStatus


def _make_submission(title, selftext="", permalink="/r/forhire/comments/abc/test", author="user1"):
    sub = MagicMock()
    sub.title = title
    sub.selftext = selftext
    sub.permalink = permalink
    sub.author = MagicMock(__str__=lambda self: author) if author else None
    return sub


def _mock_reddit_with_posts(posts_by_subreddit):
    """Return a mock Reddit instance that returns configured posts per subreddit."""
    mock_reddit = MagicMock()

    def subreddit_side_effect(name):
        sub = MagicMock()
        sub.new.return_value = posts_by_subreddit.get(name, [])
        return sub

    mock_reddit.subreddit.side_effect = subreddit_side_effect
    return mock_reddit


# ──────────────────────────────────────────────
# 1. Scrape one subreddit → posts returned > 0
# ──────────────────────────────────────────────

@patch("scraper.scraper.get_reddit")
@patch("scraper.scraper.time.sleep")
def test_scrape_one_subreddit_returns_posts(mock_sleep, mock_get_reddit):
    init_db()
    posts = {
        "forhire": [
            _make_submission("Need a developer for landing page", "Budget $500, ASAP", "/r/forhire/comments/1/t"),
            _make_submission("Looking for freelancer to build an app", "paid gig, quick fix", "/r/forhire/comments/2/t"),
            _make_submission("Random non-matching post", "just chatting", "/r/forhire/comments/3/t"),
        ],
    }
    mock_get_reddit.return_value = _mock_reddit_with_posts(posts)

    from scraper.scraper import fetch_posts
    reddit = mock_get_reddit()
    result = fetch_posts(reddit, "forhire", limit=3)
    assert len(result) > 0


# ──────────────────────────────────────────────
# 2. Scraped leads saved to test_leads.db
# ──────────────────────────────────────────────

@patch("scraper.scraper.get_reddit")
@patch("scraper.scraper.time.sleep")
@patch("scraper.scraper.SUBREDDITS", ["forhire"])
def test_scraped_leads_saved_to_db(mock_sleep, mock_get_reddit):
    init_db()
    posts = {
        "forhire": [
            _make_submission("Need a developer ASAP", "Budget is $300", "/r/forhire/comments/save1/t"),
        ],
    }
    mock_get_reddit.return_value = _mock_reddit_with_posts(posts)

    from scraper.scraper import scrape_all_subreddits
    count = scrape_all_subreddits()
    assert count >= 1

    leads = get_all_leads()
    assert len(leads) >= 1
    assert any("forhire" in l.subreddit for l in leads)


# ──────────────────────────────────────────────
# 3. No duplicate leads on second scrape
# ──────────────────────────────────────────────

@patch("scraper.scraper.get_reddit")
@patch("scraper.scraper.time.sleep")
@patch("scraper.scraper.SUBREDDITS", ["forhire"])
def test_no_duplicates_on_second_scrape(mock_sleep, mock_get_reddit):
    init_db()
    posts = {
        "forhire": [
            _make_submission("Need a developer urgently", "Budget $200", "/r/forhire/comments/dup1/t"),
        ],
    }
    mock_get_reddit.return_value = _mock_reddit_with_posts(posts)

    from scraper.scraper import scrape_all_subreddits
    first_count = scrape_all_subreddits()
    second_count = scrape_all_subreddits()

    assert first_count >= 1
    assert second_count == 0  # all duplicates skipped

    leads = get_all_leads()
    urls = [l.url for l in leads]
    assert len(urls) == len(set(urls))  # no duplicate URLs


# ──────────────────────────────────────────────
# 4. All required fields populated (none null)
# ──────────────────────────────────────────────

@patch("scraper.scraper.get_reddit")
@patch("scraper.scraper.time.sleep")
@patch("scraper.scraper.SUBREDDITS", ["forhire"])
def test_all_required_fields_populated(mock_sleep, mock_get_reddit):
    init_db()
    posts = {
        "forhire": [
            _make_submission("Looking for a developer", "paid project, budget $1000", "/r/forhire/comments/fields1/t", "real_user"),
        ],
    }
    mock_get_reddit.return_value = _mock_reddit_with_posts(posts)

    from scraper.scraper import scrape_all_subreddits
    scrape_all_subreddits()

    leads = get_all_leads()
    for lead in leads:
        assert lead.title is not None
        assert lead.url is not None
        assert lead.author is not None
        assert lead.subreddit is not None
        assert lead.scraped_at is not None
        assert lead.status is not None


# ──────────────────────────────────────────────
# 5. keywords_matched never empty on saved lead
# ──────────────────────────────────────────────

@patch("scraper.scraper.get_reddit")
@patch("scraper.scraper.time.sleep")
@patch("scraper.scraper.SUBREDDITS", ["forhire"])
def test_keywords_matched_not_empty(mock_sleep, mock_get_reddit):
    init_db()
    posts = {
        "forhire": [
            _make_submission("Need a website quick", "Budget $100, ASAP", "/r/forhire/comments/kw1/t"),
        ],
    }
    mock_get_reddit.return_value = _mock_reddit_with_posts(posts)

    from scraper.scraper import scrape_all_subreddits
    scrape_all_subreddits()

    leads = get_all_leads()
    for lead in leads:
        assert lead.keywords_matched is not None
        assert lead.keywords_matched != ""


# ──────────────────────────────────────────────
# 6. Scrape all 10 subreddits → total leads > 0
# ──────────────────────────────────────────────

@patch("scraper.scraper.get_reddit")
@patch("scraper.scraper.time.sleep")
def test_scrape_all_10_subreddits(mock_sleep, mock_get_reddit):
    init_db()
    from config.subreddits import SUBREDDITS
    posts = {}
    for i, sub in enumerate(SUBREDDITS):
        posts[sub] = [
            _make_submission(
                f"Need a developer for {sub} project",
                "Budget $500, paid gig",
                f"/r/{sub}/comments/all{i}/t",
            ),
        ]
    mock_get_reddit.return_value = _mock_reddit_with_posts(posts)

    from scraper.scraper import scrape_all_subreddits
    total = scrape_all_subreddits()
    assert total > 0

    leads = get_all_leads()
    assert len(leads) > 0


# ──────────────────────────────────────────────
# 7. Follow-up tab query returns correct leads
# ──────────────────────────────────────────────

def test_follow_up_query_returns_overdue_leads():
    init_db()
    session = db_mod.SessionLocal()
    try:
        # Insert a lead with overdue follow_up_due
        overdue_lead = Lead(
            title="Overdue Lead",
            url="https://reddit.com/r/test/overdue1",
            author="test_author",
            subreddit="forhire",
            post_body="test body",
            keywords_matched="budget",
            status=LeadStatus.CONTACTED,
            contacted_at=datetime.utcnow() - timedelta(days=5),
            follow_up_due=datetime.utcnow() - timedelta(days=2),
        )
        # Insert a lead with future follow_up_due (not overdue)
        future_lead = Lead(
            title="Future Lead",
            url="https://reddit.com/r/test/future1",
            author="test_author",
            subreddit="forhire",
            post_body="test body",
            keywords_matched="budget",
            status=LeadStatus.CONTACTED,
            contacted_at=datetime.utcnow(),
            follow_up_due=datetime.utcnow() + timedelta(days=3),
        )
        session.add_all([overdue_lead, future_lead])
        session.commit()
    finally:
        session.close()

    now = datetime.utcnow()
    all_leads = get_all_leads()
    overdue = [
        l for l in all_leads
        if l.follow_up_due and l.follow_up_due <= now
        and l.status not in (LeadStatus.CONVERTED, LeadStatus.DEAD)
    ]
    assert len(overdue) == 1
    assert overdue[0].title == "Overdue Lead"
