import os
import time
import logging
import requests
from config.keywords import INCLUDE_KEYWORDS, EXCLUDE_KEYWORDS
from config.subreddits import SUBREDDITS
from db.database import SessionLocal

logger = logging.getLogger(__name__)

REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "GigFinder/1.0")
REDDIT_JSON_URL = "https://www.reddit.com/r/{subreddit}/new.json"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": REDDIT_USER_AGENT})


def fetch_posts(subreddit_name, limit=50):
    """Fetch the latest posts from a subreddit using the public Reddit JSON API."""
    logger.debug("Fetching %d posts from r/%s", limit, subreddit_name)
    url = REDDIT_JSON_URL.format(subreddit=subreddit_name)
    try:
        response = SESSION.get(url, params={"limit": limit}, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Failed to fetch r/%s: %s", subreddit_name, exc)
        return []

    posts = []
    for child in response.json().get("data", {}).get("children", []):
        data = child.get("data", {})
        author = data.get("author", "[deleted]") or "[deleted]"
        selftext = data.get("selftext", "") or ""
        posts.append({
            "title": data.get("title", ""),
            "url": f"https://www.reddit.com{data.get('permalink', '')}",
            "author": author,
            "subreddit": subreddit_name,
            "post_body": selftext[:500],
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
    total_saved = 0
    for subreddit_name in SUBREDDITS:
        logger.info("Scraping r/%s ...", subreddit_name)
        posts = fetch_posts(subreddit_name)
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
