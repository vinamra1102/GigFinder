"""Integration tests: exercise the full scraper → DB pipeline with mocked HTTP requests."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import db.database as db_mod
from db.database import get_all_leads, init_db
from db.models import Lead, LeadStatus


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
# 1. Scrape one subreddit → posts returned > 0
# ──────────────────────────────────────────────

@patch("scraper.scraper.SESSION")
def test_scrape_one_subreddit_returns_posts(mock_session):
    init_db()
    mock_session.get.return_value = _make_response([
        _post_data("Need a developer for landing page", "Budget $500, ASAP", "/r/forhire/comments/1/t"),
        _post_data("Looking for freelancer to build an app", "paid gig, quick fix", "/r/forhire/comments/2/t"),
        _post_data("Random non-matching post", "just chatting", "/r/forhire/comments/3/t"),
    ])
    from scraper.scraper import fetch_posts
    result = fetch_posts("forhire", limit=3)
    assert len(result) > 0


# ──────────────────────────────────────────────
# 2. Scraped leads saved to test_leads.db
# ──────────────────────────────────────────────

@patch("scraper.scraper.time.sleep")
@patch("scraper.scraper.SUBREDDITS", ["forhire"])
@patch("scraper.scraper.SESSION")
def test_scraped_leads_saved_to_db(mock_session, mock_sleep):
    init_db()
    mock_session.get.return_value = _make_response([
        _post_data("Need a developer ASAP", "Budget is $300", "/r/forhire/comments/save1/t"),
    ])
    from scraper.scraper import scrape_all_subreddits
    count = scrape_all_subreddits()
    assert count >= 1
    leads = get_all_leads()
    assert len(leads) >= 1
    assert any("forhire" in l.subreddit for l in leads)


# ──────────────────────────────────────────────
# 3. No duplicate leads on second scrape
# ──────────────────────────────────────────────

@patch("scraper.scraper.time.sleep")
@patch("scraper.scraper.SUBREDDITS", ["forhire"])
@patch("scraper.scraper.SESSION")
def test_no_duplicates_on_second_scrape(mock_session, mock_sleep):
    init_db()
    mock_session.get.return_value = _make_response([
        _post_data("Need a developer urgently", "Budget $200", "/r/forhire/comments/dup1/t"),
    ])
    from scraper.scraper import scrape_all_subreddits
    first_count = scrape_all_subreddits()
    second_count = scrape_all_subreddits()

    assert first_count >= 1
    assert second_count == 0

    leads = get_all_leads()
    urls = [l.url for l in leads]
    assert len(urls) == len(set(urls))


# ──────────────────────────────────────────────
# 4. All required fields populated (none null)
# ──────────────────────────────────────────────

@patch("scraper.scraper.time.sleep")
@patch("scraper.scraper.SUBREDDITS", ["forhire"])
@patch("scraper.scraper.SESSION")
def test_all_required_fields_populated(mock_session, mock_sleep):
    init_db()
    mock_session.get.return_value = _make_response([
        _post_data("Looking for a developer", "paid project, budget $1000", "/r/forhire/comments/fields1/t", "real_user"),
    ])
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

@patch("scraper.scraper.time.sleep")
@patch("scraper.scraper.SUBREDDITS", ["forhire"])
@patch("scraper.scraper.SESSION")
def test_keywords_matched_not_empty(mock_session, mock_sleep):
    init_db()
    mock_session.get.return_value = _make_response([
        _post_data("Need a website quick", "Budget $100, ASAP", "/r/forhire/comments/kw1/t"),
    ])
    from scraper.scraper import scrape_all_subreddits
    scrape_all_subreddits()

    leads = get_all_leads()
    for lead in leads:
        assert lead.keywords_matched is not None
        assert lead.keywords_matched != ""


# ──────────────────────────────────────────────
# 6. Scrape all 11 subreddits → total leads > 0
# ──────────────────────────────────────────────

@patch("scraper.scraper.time.sleep")
@patch("scraper.scraper.SESSION")
def test_scrape_all_subreddits(mock_session, mock_sleep):
    init_db()
    from config.subreddits import SUBREDDITS

    def make_sub_response(url, **kwargs):
        subreddit = url.split("/r/")[1].split("/")[0]
        i = SUBREDDITS.index(subreddit) if subreddit in SUBREDDITS else 0
        return _make_response([
            _post_data(
                f"Need a developer for {subreddit} project",
                "Budget $500, paid gig",
                f"/r/{subreddit}/comments/all{i}/t",
            )
        ])

    mock_session.get.side_effect = make_sub_response

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
