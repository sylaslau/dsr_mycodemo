"""Environment: the same section Start a batch now shows below the pick (this page goes in the 5-page flow)."""

import streamlit as st

from dsr_mycodemo.app import flow, stage_ui

st.set_page_config(page_title="Environment", page_icon="📦", layout="wide")
flow.init()
ss = st.session_state
flow.need("choice", "Start a batch", "pages/1_Start_a_batch.py")
flow.step_header(2, 8, "Environment")
stage_ui.environment_section()
if ss["environment"]:
    if st.button("Next: recipe and actions", type="primary", key="next"):
        st.switch_page("pages/3_Recipe_and_timeline.py")
else:
    st.caption("Choose where you grow to continue.")
