from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:///gigfinder.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables defined in models."""
    import db.models  # noqa: F401 — ensure models are registered before create_all
    Base.metadata.create_all(bind=engine)


def get_all_leads(status=None, subreddit=None, date_from=None, date_to=None):
    """Return leads with optional filters for status, subreddit, and date range."""
    from db.models import Lead
    db = SessionLocal()
    try:
        query = db.query(Lead)
        if status:
            query = query.filter(Lead.status == status)
        if subreddit:
            query = query.filter(Lead.subreddit == subreddit)
        if date_from:
            query = query.filter(Lead.scraped_at >= date_from)
        if date_to:
            query = query.filter(Lead.scraped_at <= date_to)
        return query.order_by(Lead.scraped_at.desc()).all()
    finally:
        db.close()


def update_lead_status(lead_id, new_status):
    """Update a lead's status; auto-sets contacted_at and follow_up_due when moving to contacted."""
    from db.models import Lead, LeadStatus
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return False
        if new_status == LeadStatus.CONTACTED:
            lead.set_contacted()
        else:
            lead.status = new_status
        db.commit()
        return True
    finally:
        db.close()


def update_lead_notes(lead_id, notes):
    """Persist free-text notes for a lead."""
    from db.models import Lead
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return False
        lead.notes = notes
        db.commit()
        return True
    finally:
        db.close()
