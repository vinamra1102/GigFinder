import os
import time
import logging
import praw
from dotenv import load_dotenv
from config.keywords import INCLUDE_KEYWORDS, EXCLUDE_KEYWORDS
from config.subreddits import SUBREDDITS
from db.database import SessionLocal

load_dotenv()

logger = logging.getLogger(__name__)


def get_reddit():
    """Return a read-only PRAW Reddit instance using .env credentials."""
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT", "GigFinder/1.0"),
    )


def fetch_posts(reddit, subreddit_name, limit=50):
    """Fetch the latest `limit` new posts from a subreddit and return raw post data."""
    logger.debug("Fetching %d posts from r/%s", limit, subreddit_name)
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
    logger.debug("Fetched %d posts from r/%s", len(posts), subreddit_name)
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
        logger.info("Saved lead: %s", post["title"][:60])
    finally:
        db.close()


def scrape_all_subreddits():
    """Iterate over all configured subreddits, filter posts, and save qualifying leads."""
    logger.info("Starting scrape of %d subreddits", len(SUBREDDITS))
    reddit = get_reddit()
    total_saved = 0
    for subreddit_name in SUBREDDITS:
        logger.info("Scraping r/%s ...", subreddit_name)
        posts = fetch_posts(reddit, subreddit_name)
        saved = 0
        for post in posts:
            if has_exclude_keywords(post):
                logger.debug("Excluded (keyword): %s", post["title"][:60])
                continue
            matched = matches_include_keywords(post)
            if not matched:
                continue
            if url_exists(post["url"]):
                logger.debug("Duplicate skipped: %s", post["url"])
                continue
            keywords_matched = build_keywords_matched(post)
            save_lead(post, keywords_matched)
            saved += 1
        logger.info("r/%s: saved %d new leads", subreddit_name, saved)
        total_saved += saved
        time.sleep(2)  # respect Reddit rate limits between subreddit fetches
    logger.info("Scrape complete — %d total new leads saved", total_saved)
    return total_saved
