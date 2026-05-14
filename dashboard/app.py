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
stats_cols[0].metric("Leads Today", len(leads_today))
