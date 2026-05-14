from datetime import timedelta

import db.database as db_mod
from db.database import init_db, get_all_leads, update_lead_status, update_lead_notes
from db.models import Lead, LeadStatus, FOLLOW_UP_DAYS


def _insert_lead(url="https://reddit.com/r/test/1", title="Test Lead", **overrides):
    """Helper: insert a lead directly into the test DB."""
    session = db_mod.SessionLocal()
    try:
        lead = Lead(
            title=title,
            url=url,
            author=overrides.get("author", "test_author"),
            subreddit=overrides.get("subreddit", "forhire"),
            post_body=overrides.get("post_body", "test body"),
            keywords_matched=overrides.get("keywords_matched", "budget"),
            status=overrides.get("status", LeadStatus.NEW),
        )
        session.add(lead)
        session.commit()
        session.refresh(lead)
        return lead.id
    finally:
        session.close()


# ──────────────────────────────────────────────
# 1. init_db creates tables without error
# ──────────────────────────────────────────────

def test_init_db_creates_tables(test_database):
    from sqlalchemy import inspect
    init_db()
    inspector = inspect(test_database)
    tables = inspector.get_table_names()
    assert "leads" in tables


# ──────────────────────────────────────────────
# 2. save_lead inserts a dummy lead correctly
# ──────────────────────────────────────────────

def test_insert_lead():
    lead_id = _insert_lead()
    session = db_mod.SessionLocal()
    try:
        lead = session.query(Lead).filter(Lead.id == lead_id).first()
        assert lead is not None
        assert lead.title == "Test Lead"
        assert lead.status == LeadStatus.NEW
        assert lead.url == "https://reddit.com/r/test/1"
    finally:
        session.close()


# ──────────────────────────────────────────────
# 3. Duplicate URL check prevents double insert
# ──────────────────────────────────────────────

def test_duplicate_url_rejected():
    import pytest
    from sqlalchemy.exc import IntegrityError
    _insert_lead(url="https://reddit.com/r/test/dup")
    with pytest.raises(IntegrityError):
        _insert_lead(url="https://reddit.com/r/test/dup")


# ──────────────────────────────────────────────
# 4. update_lead_status for all 5 statuses
# ──────────────────────────────────────────────

def test_update_status_new():
    lid = _insert_lead(url="https://reddit.com/r/test/s1")
    assert update_lead_status(lid, LeadStatus.NEW) is True
    leads = get_all_leads()
    assert any(l.id == lid and l.status == LeadStatus.NEW for l in leads)


def test_update_status_contacted():
    lid = _insert_lead(url="https://reddit.com/r/test/s2")
    assert update_lead_status(lid, LeadStatus.CONTACTED) is True
    session = db_mod.SessionLocal()
    try:
        lead = session.query(Lead).filter(Lead.id == lid).first()
        assert lead.status == LeadStatus.CONTACTED
        assert lead.contacted_at is not None
        assert lead.follow_up_due is not None
    finally:
        session.close()


def test_update_status_follow_up():
    lid = _insert_lead(url="https://reddit.com/r/test/s3")
    assert update_lead_status(lid, LeadStatus.FOLLOW_UP) is True
    session = db_mod.SessionLocal()
    try:
        lead = session.query(Lead).filter(Lead.id == lid).first()
        assert lead.status == LeadStatus.FOLLOW_UP
    finally:
        session.close()


def test_update_status_converted():
    lid = _insert_lead(url="https://reddit.com/r/test/s4")
    assert update_lead_status(lid, LeadStatus.CONVERTED) is True
    session = db_mod.SessionLocal()
    try:
        lead = session.query(Lead).filter(Lead.id == lid).first()
        assert lead.status == LeadStatus.CONVERTED
    finally:
        session.close()


def test_update_status_dead():
    lid = _insert_lead(url="https://reddit.com/r/test/s5")
    assert update_lead_status(lid, LeadStatus.DEAD) is True
    session = db_mod.SessionLocal()
    try:
        lead = session.query(Lead).filter(Lead.id == lid).first()
        assert lead.status == LeadStatus.DEAD
    finally:
        session.close()


def test_update_status_nonexistent_lead():
    assert update_lead_status(99999, LeadStatus.NEW) is False


# ──────────────────────────────────────────────
# 5. update_lead_notes saves and retrieves notes
# ──────────────────────────────────────────────

def test_update_notes():
    lid = _insert_lead(url="https://reddit.com/r/test/n1")
    assert update_lead_notes(lid, "Contacted via DM") is True
    session = db_mod.SessionLocal()
    try:
        lead = session.query(Lead).filter(Lead.id == lid).first()
        assert lead.notes == "Contacted via DM"
    finally:
        session.close()


def test_update_notes_nonexistent_lead():
    assert update_lead_notes(99999, "ghost") is False


# ──────────────────────────────────────────────
# 6. follow_up_due = contacted_at + 3 days
# ──────────────────────────────────────────────

def test_follow_up_due_is_contacted_at_plus_3_days():
    lid = _insert_lead(url="https://reddit.com/r/test/fu1")
    update_lead_status(lid, LeadStatus.CONTACTED)
    session = db_mod.SessionLocal()
    try:
        lead = session.query(Lead).filter(Lead.id == lid).first()
        expected = lead.contacted_at + timedelta(days=FOLLOW_UP_DAYS)
        assert abs((lead.follow_up_due - expected).total_seconds()) < 1
    finally:
        session.close()


# ──────────────────────────────────────────────
# 7. get_all_leads returns all inserted leads
# ──────────────────────────────────────────────

def test_get_all_leads_returns_all():
    _insert_lead(url="https://reddit.com/r/test/a1")
    _insert_lead(url="https://reddit.com/r/test/a2")
    _insert_lead(url="https://reddit.com/r/test/a3")
    leads = get_all_leads()
    assert len(leads) == 3


# ──────────────────────────────────────────────
# 8. get_all_leads with status filter
# ──────────────────────────────────────────────

def test_get_all_leads_status_filter():
    _insert_lead(url="https://reddit.com/r/test/f1", status=LeadStatus.NEW)
    _insert_lead(url="https://reddit.com/r/test/f2", status=LeadStatus.NEW)
    lid3 = _insert_lead(url="https://reddit.com/r/test/f3")
    update_lead_status(lid3, LeadStatus.CONTACTED)

    new_leads = get_all_leads(status=LeadStatus.NEW)
    assert len(new_leads) == 2
    assert all(l.status == LeadStatus.NEW for l in new_leads)

    contacted_leads = get_all_leads(status=LeadStatus.CONTACTED)
    assert len(contacted_leads) == 1
    assert contacted_leads[0].status == LeadStatus.CONTACTED
