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

## Subreddits Monitored

`r/forhire`, `r/hiring`, `r/webdev`, `r/androiddev`, `r/reactjs`, `r/learnprogramming`, `r/sveltejs`, `r/node`, `r/freelance`, `r/graphic_design`

## Quick Start

### 1. Clone and install dependencies

```bash
git clone https://github.com/vinamra1102/GigFinder.git
cd GigFinder
pip install -r requirements.txt
```

### 2. Set up Reddit API credentials

Copy `.env.example` to `.env` and fill in your Reddit API credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=GigFinder/1.0
```

### 3. Run the scraper manually

```bash
python main.py
```

### 4. Launch the dashboard

```bash
streamlit run dashboard/app.py
```

## Project Structure

```
GigFinder/
├── config/
│   ├── subreddits.py     # List of subreddits to scrape
│   └── keywords.py       # Include/exclude keyword filters
├── db/
│   ├── database.py       # SQLite connection setup
│   └── models.py         # Lead model and ORM
├── scraper/
│   └── scraper.py        # PRAW scraper logic
├── dashboard/
│   └── app.py            # Streamlit dashboard
├── main.py               # Entry point + scheduler
├── .env.example          # Credential template
└── requirements.txt
```

## Lead Pipeline Statuses

| Status | Meaning |
|--------|---------|
| `new` | Freshly scraped, not yet reviewed |
| `contacted` | You have reached out |
| `follow_up` | Awaiting a response |
| `converted` | Turned into a paid gig |
| `dead` | Not a fit / no response |
