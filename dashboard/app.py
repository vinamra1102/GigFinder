import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime, timedelta
import streamlit as st
from db.database import get_all_leads, update_lead_status, update_lead_notes, init_db
from db.models import LeadStatus

init_db()

st.set_page_config(
    page_title="GigFinder",
    page_icon="🔍",
    layout="wide",
)

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
    # Status filter
    status_options = ["All"] + LeadStatus.ALL
    selected_status = st.selectbox("Filter by Status", status_options, key="status_filter")

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
