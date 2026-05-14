# Dashboard Manual Test Checklist

Run the dashboard with: `streamlit run dashboard/app.py`

## General
- [ ] Dashboard loads without error at http://localhost:8501
- [ ] Page title shows "GigFinder — Reddit Freelance Lead Tracker"
- [ ] Wide layout is applied correctly

## Stats Bar
- [ ] "Leads Today" count matches leads scraped today
- [ ] "Total Leads" count matches total in DB
- [ ] "New" count matches leads with status = new
- [ ] "Contacted" count matches leads with status = contacted
- [ ] "Converted" count matches leads with status = converted

## Leads Table
- [ ] All leads display in the table with correct columns
- [ ] Columns include: ID, Title, Subreddit, Author, Status, Keywords, Scraped At, Contacted At, Follow-up Due

## Filters
- [ ] Filter by Status works for "All"
- [ ] Filter by Status works for "new"
- [ ] Filter by Status works for "contacted"
- [ ] Filter by Status works for "follow_up"
- [ ] Filter by Status works for "converted"
- [ ] Filter by Status works for "dead"
- [ ] Filter by Subreddit dropdown lists all subreddits from DB
- [ ] Filter by Subreddit correctly narrows results
- [ ] Date range "From Date" picker works
- [ ] Date range "To Date" picker works
- [ ] Combining all three filters works correctly

## Lead Expander
- [ ] Clicking a lead title expands to show details
- [ ] Post body text displays correctly
- [ ] Color-coded status badge is visible
- [ ] "Open Reddit Post" link button is present and clickable

## Status Update
- [ ] Status dropdown shows current status as default
- [ ] Changing status updates the DB immediately
- [ ] Setting status to "contacted" auto-sets contacted_at
- [ ] Setting status to "contacted" auto-sets follow_up_due (contacted_at + 3 days)

## Notes
- [ ] Notes text area shows existing notes
- [ ] Typing new notes and clicking "Save Notes" persists
- [ ] Notes survive a page refresh

## Follow-up Due Tab
- [ ] Tab switches correctly to "Follow-up Due"
- [ ] Shows only leads where follow_up_due <= now
- [ ] Does NOT show converted or dead leads
- [ ] Shows warning with count of overdue leads
- [ ] Each overdue lead expander shows follow-up date and Reddit link

## Sidebar — Run Scraper Now
- [ ] "Run Scraper Now" button is visible in sidebar
- [ ] Clicking it triggers the scraper (spinner shown)
- [ ] Success toast shows count of new leads saved
- [ ] Error toast shows if scraper fails (e.g., invalid credentials)
- [ ] Page reruns after successful scrape to show new leads

## Empty States
- [ ] When no leads exist: "No leads yet. Click Run Scraper Now..." message shown
- [ ] When filters return no results: "No leads match the current filters..." message shown
- [ ] Follow-up tab with no overdue leads: "No overdue follow-ups. You're all caught up!" shown
