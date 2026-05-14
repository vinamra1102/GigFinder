import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "test_leads.db")
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"


@pytest.fixture(autouse=True)
def test_database():
    """Redirect all DB operations to test_leads.db for every test."""
    import db.database as db_mod

    original_engine = db_mod.engine
    original_session = db_mod.SessionLocal

    test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    test_session = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

    db_mod.engine = test_engine
    db_mod.SessionLocal = test_session

    from db.database import Base
    Base.metadata.create_all(bind=test_engine)

    yield test_engine

    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()

    db_mod.engine = original_engine
    db_mod.SessionLocal = original_session

    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.fixture
def sample_post():
    """A realistic post dict matching the scraper output format."""
    return {
        "title": "Looking for a developer to build a landing page",
        "url": "https://www.reddit.com/r/forhire/comments/abc123/test",
        "author": "test_user",
        "subreddit": "forhire",
        "post_body": "I need a website built ASAP. Budget is $500. Simple landing page.",
    }


@pytest.fixture
def sample_post_exclude():
    """A post that should be excluded by exclude keywords."""
    return {
        "title": "Looking for a co-founder for long term project",
        "url": "https://www.reddit.com/r/forhire/comments/xyz789/test",
        "author": "equity_guy",
        "subreddit": "forhire",
        "post_body": "Need someone for equity. Full time commitment for months.",
    }
