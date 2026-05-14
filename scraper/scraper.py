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
