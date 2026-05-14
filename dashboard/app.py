import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

st.set_page_config(
    page_title="GigFinder",
    page_icon="🔍",
    layout="wide",
)

st.title("GigFinder — Reddit Freelance Lead Tracker")
st.markdown("---")

# Stats bar (populated in subsequent steps)
stats_cols = st.columns(5)
