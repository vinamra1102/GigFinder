import os
import praw
from dotenv import load_dotenv

load_dotenv()


def get_reddit():
    """Return a read-only PRAW Reddit instance using .env credentials."""
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT", "GigFinder/1.0"),
    )
