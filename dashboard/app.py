import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime, timedelta
import streamlit as st
from db.database import get_all_leads, update_lead_status, update_lead_notes, init_db
from db.models import LeadStatus

init_db()


STATUS_COLORS = {
    "new": "#1f77b4",
    "contacted": "#ff7f0e",
    "follow_up": "#9467bd",
    "converted": "#2ca02c",
    "dead": "#d62728",
}


def status_badge(status):
    color = STATUS_COLORS.get(status, "#888888")
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:0.8em">{status.upper()}</span>'


def run_scraper_now():
    try:
        from scraper.scraper import scrape_all_subreddits
        count = scrape_all_subreddits()
        return count, None
    except Exception as e:
        return None, str(e)


st.set_page_config(
    page_title="GigFinder",
    page_icon="🔍",
    layout="wide",
)

with st.sidebar:
    st.header("Actions")
    if st.button("Run Scraper Now", use_container_width=True):
        with st.spinner("Scraping Reddit..."):
            count, error = run_scraper_now()
        if error:
            st.toast(f"Scrape failed: {error}", icon="❌")
        else:
            st.toast(f"Done! {count} new lead(s) saved.", icon="✅")
            st.rerun()

st.title("GigFinder — Reddit Freelance Lead Tracker")
st.markdown("---")

all_leads = get_all_leads()
today = date.today()
leads_today = [l for l in all_leads if l.scraped_at and l.scraped_at.date() == today]

# Stats bar
stats_cols = st.columns(5)
new_count = sum(1 for l in all_leads if l.status == LeadStatus.NEW)
contacted_count = sum(1 for l in all_leads if l.status == LeadStatus.CONTACTED)
converted_count = sum(1 for l in all_leads if l.status == LeadStatus.CONVERTED)
total_count = len(all_leads)

stats_cols[0].metric("Leads Today", len(leads_today))
stats_cols[1].metric("Total Leads", total_count)
stats_cols[2].metric("New", new_count)
stats_cols[3].metric("Contacted", contacted_count)
stats_cols[4].metric("Converted", converted_count)

st.markdown("---")

# Leads table (filters applied below)
tab_leads, tab_followup = st.tabs(["All Leads", "Follow-up Due"])

with tab_leads:
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    # Status filter
    status_options = ["All"] + LeadStatus.ALL
    selected_status = filter_col1.selectbox("Filter by Status", status_options, key="status_filter")

    # Subreddit filter
    subreddits_in_db = sorted(set(l.subreddit for l in all_leads))
    subreddit_options = ["All"] + subreddits_in_db
    selected_subreddit = filter_col2.selectbox("Filter by Subreddit", subreddit_options, key="subreddit_filter")

    # Date range filter
    date_from = filter_col3.date_input("From Date", value=today - timedelta(days=30), key="date_from")
    date_to = filter_col3.date_input("To Date", value=today, key="date_to")

    # Apply filters
    filtered_leads = all_leads
    if selected_status != "All":
        filtered_leads = [l for l in filtered_leads if l.status == selected_status]
    if selected_subreddit != "All":
        filtered_leads = [l for l in filtered_leads if l.subreddit == selected_subreddit]
    filtered_leads = [
        l for l in filtered_leads
        if l.scraped_at and date_from <= l.scraped_at.date() <= date_to
    ]

    if not filtered_leads:
        st.info("No leads found. Run the scraper to populate leads.")
    else:
        import pandas as pd
        table_data = []
        for lead in filtered_leads:
            table_data.append({
                "ID": lead.id,
                "Title": lead.title[:80],
                "Subreddit": lead.subreddit,
                "Author": lead.author,
                "Status": lead.status,
                "Keywords": lead.keywords_matched or "",
                "Scraped At": lead.scraped_at.strftime("%Y-%m-%d %H:%M") if lead.scraped_at else "",
                "Contacted At": lead.contacted_at.strftime("%Y-%m-%d") if lead.contacted_at else "",
                "Follow-up Due": lead.follow_up_due.strftime("%Y-%m-%d") if lead.follow_up_due else "",
            })
        st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

        st.markdown("### Lead Details")
        for lead in filtered_leads:
            with st.expander(f"{lead.title[:90]}"):
                st.markdown(status_badge(lead.status), unsafe_allow_html=True)
                st.markdown(f"**Subreddit:** r/{lead.subreddit} | **Author:** u/{lead.author}")
                st.markdown(f"**Scraped:** {lead.scraped_at.strftime('%Y-%m-%d %H:%M') if lead.scraped_at else 'N/A'}")
                st.markdown("**Post Body:**")
                st.text(lead.post_body or "(no body)")
                st.link_button("Open Reddit Post", lead.url)

                st.markdown("**Update Status:**")
                current_idx = LeadStatus.ALL.index(lead.status) if lead.status in LeadStatus.ALL else 0
                new_status = st.selectbox(
                    "Status",
                    LeadStatus.ALL,
                    index=current_idx,
                    key=f"status_{lead.id}",
                    label_visibility="collapsed",
                )
                if new_status != lead.status:
                    if update_lead_status(lead.id, new_status):
                        st.success(f"Status updated to '{new_status}'")
                        if new_status == LeadStatus.CONTACTED:
                            st.info("contacted_at and follow_up_due auto-set (+3 days).")
                        st.rerun()

                st.markdown("**Notes:**")
                notes_text = st.text_area(
                    "Notes",
                    value=lead.notes or "",
                    key=f"notes_{lead.id}",
                    label_visibility="collapsed",
                    height=80,
                )
                if st.button("Save Notes", key=f"save_notes_{lead.id}"):
                    if update_lead_notes(lead.id, notes_text):
                        st.success("Notes saved.")
                        st.rerun()
                    else:
                        st.error("Failed to save notes.")

with tab_followup:
    now = datetime.utcnow()
    overdue_leads = [
        l for l in all_leads
        if l.follow_up_due and l.follow_up_due <= now
        and l.status not in (LeadStatus.CONVERTED, LeadStatus.DEAD)
    ]
    if not overdue_leads:
        st.info("No overdue follow-ups. You're all caught up!")
    else:
        st.warning(f"{len(overdue_leads)} lead(s) need follow-up.")
        for lead in overdue_leads:
            with st.expander(f"[OVERDUE] {lead.title[:90]}"):
                st.markdown(f"**Subreddit:** r/{lead.subreddit} | **Author:** u/{lead.author}")
                st.markdown(f"**Follow-up was due:** {lead.follow_up_due.strftime('%Y-%m-%d')}")
                st.markdown(f"**Status:** {lead.status}")
                st.link_button("Open Reddit Post", lead.url)
