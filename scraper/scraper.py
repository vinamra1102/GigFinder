import os
import praw
from dotenv import load_dotenv
from config.keywords import INCLUDE_KEYWORDS, EXCLUDE_KEYWORDS
from db.database import SessionLocal

load_dotenv()


def get_reddit():
    """Return a read-only PRAW Reddit instance using .env credentials."""
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT", "GigFinder/1.0"),
    )


def fetch_posts(reddit, subreddit_name, limit=50):
    """Fetch the latest `limit` new posts from a subreddit and return raw post data."""
    posts = []
    subreddit = reddit.subreddit(subreddit_name)
    for submission in subreddit.new(limit=limit):
        posts.append({
            "title": submission.title,
            "url": f"https://www.reddit.com{submission.permalink}",
            "author": str(submission.author) if submission.author else "[deleted]",
            "subreddit": subreddit_name,
            "post_body": submission.selftext[:500] if submission.selftext else "",
        })
    return posts


def matches_include_keywords(post):
    """Return list of matched include keywords found in title or body (case-insensitive)."""
    text = (post["title"] + " " + post["post_body"]).lower()
    return [kw for kw in INCLUDE_KEYWORDS if kw.lower() in text]


def has_exclude_keywords(post):
    """Return True if any exclude keyword is found in title or body (case-insensitive)."""
    text = (post["title"] + " " + post["post_body"]).lower()
    return any(kw.lower() in text for kw in EXCLUDE_KEYWORDS)


def build_keywords_matched(post):
    """Return comma-separated string of all include keywords matched in this post."""
    matched = matches_include_keywords(post)
    return ", ".join(matched) if matched else ""


def url_exists(url):
    """Return True if a lead with this URL already exists in the database."""
    from db.models import Lead
    db = SessionLocal()
    try:
        return db.query(Lead).filter(Lead.url == url).first() is not None
    finally:
        db.close()


def save_lead(post, keywords_matched):
    """Insert a new lead into the database."""
    from db.models import Lead
    db = SessionLocal()
    try:
        lead = Lead(
            title=post["title"],
            url=post["url"],
            author=post["author"],
            subreddit=post["subreddit"],
            post_body=post["post_body"],
            keywords_matched=keywords_matched,
        )
        db.add(lead)
        db.commit()
    finally:
        db.close()
