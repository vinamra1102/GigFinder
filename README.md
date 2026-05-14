# GigFinder

A Reddit lead scraper for freelance job discovery with a Streamlit dashboard and lead pipeline tracker.

## What It Does

GigFinder automatically scrapes Reddit for freelance job opportunities across 10 developer-focused subreddits. It filters posts using include/exclude keywords, stores leads in a local SQLite database, and presents them in an interactive Streamlit dashboard where you can track each lead through a pipeline (new → contacted → follow_up → converted / dead).

## Tech Stack

- **Python** — core language
- **PRAW** — Reddit API wrapper (read-only mode)
- **SQLite + SQLAlchemy** — local database
- **Streamlit** — interactive dashboard
- **APScheduler** — daily auto-scrape at 7 AM
- **python-dotenv** — credential management

## Quick Start

### 1. Clone and install dependencies

```bash
git clone https://github.com/vinamra1102/GigFinder.git
cd GigFinder
pip install -r requirements.txt
```

### 2. Set up Reddit API credentials

Copy `.env.example` to `.env`:

```bash
cp .env.example .env   # Linux/macOS
copy .env.example .env  # Windows
```

Edit `.env` and fill in your Reddit credentials:

```
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=GigFinder/1.0
```

### 3. Run the scraper once (manual)

```bash
python main.py
```

### 4. Run the scraper on a daily schedule (7 AM)

```bash
python main.py --schedule
```

### 5. Launch the Streamlit dashboard

```bash
streamlit run dashboard/app.py
```

The dashboard opens at `http://localhost:8501`.

---

## How to Get Reddit API Credentials

1. Go to [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Scroll to the bottom and click **"are you a developer? create an app..."**
3. Fill in the form:
   - **Name:** GigFinder (or any name)
   - **App type:** select **script**
   - **Redirect URI:** `http://localhost:8080`
4. Click **Create app**
5. You'll see your new app listed:
   - **client_id** — the string just below your app name (e.g. `abc123XYZ`)
   - **client_secret** — labeled "secret"
6. Copy both values into your `.env` file

> GigFinder uses **read-only** PRAW mode — it never posts, votes, or logs into Reddit.

---

## Subreddits Monitored

`r/forhire`, `r/hiring`, `r/webdev`, `r/androiddev`, `r/reactjs`, `r/learnprogramming`, `r/sveltejs`, `r/node`, `r/freelance`, `r/graphic_design`

## Lead Pipeline Statuses

| Status | Color | Meaning |
|--------|-------|---------|
| `new` | Blue | Freshly scraped, not yet reviewed |
| `contacted` | Orange | You have reached out |
| `follow_up` | Purple | Awaiting a response |
| `converted` | Green | Turned into a paid gig |
| `dead` | Red | Not a fit / no response |

## Project Structure

```
GigFinder/
├── config/
│   ├── subreddits.py     # List of subreddits to scrape
│   └── keywords.py       # Include/exclude keyword filters
├── db/
│   ├── database.py       # SQLite connection, queries
│   └── models.py         # Lead ORM model + LeadStatus enum
├── scraper/
│   └── scraper.py        # PRAW scraper, keyword filtering, DB writes
├── dashboard/
│   └── app.py            # Streamlit dashboard
├── main.py               # Entry point + APScheduler
├── .env.example          # Credential template
└── requirements.txt
```

## Dashboard Features

- **Stats bar** — Leads today, total, new, contacted, converted
- **All Leads tab** — filterable table + expandable detail per lead
  - Filter by status, subreddit, date range
  - Color-coded status badges
  - One-click status updates (auto-sets `contacted_at` and `follow_up_due`)
  - Per-lead notes with save button
  - Direct link to Reddit post
- **Follow-up Due tab** — overdue leads that need action
- **Sidebar** — "Run Scraper Now" manual trigger with toast feedback
