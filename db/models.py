from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Text, DateTime
from db.database import Base

FOLLOW_UP_DAYS = 3


class LeadStatus:
    NEW = "new"
    CONTACTED = "contacted"
    FOLLOW_UP = "follow_up"
    CONVERTED = "converted"
    DEAD = "dead"

    ALL = [NEW, CONTACTED, FOLLOW_UP, CONVERTED, DEAD]


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    url = Column(String, unique=True, nullable=False)
    author = Column(String, nullable=False)
    subreddit = Column(String, nullable=False)
    post_body = Column(Text, nullable=True)
    keywords_matched = Column(String, nullable=True)
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String, default="new", nullable=False)
    notes = Column(Text, nullable=True)
    contacted_at = Column(DateTime, nullable=True)
    follow_up_due = Column(DateTime, nullable=True)

    def set_contacted(self):
        """Mark as contacted and auto-calculate follow_up_due (contacted_at + 3 days)."""
        self.contacted_at = datetime.utcnow()
        self.follow_up_due = self.contacted_at + timedelta(days=FOLLOW_UP_DAYS)
        self.status = LeadStatus.CONTACTED

    def __repr__(self):
        return f"<Lead id={self.id} status={self.status} subreddit={self.subreddit}>"
