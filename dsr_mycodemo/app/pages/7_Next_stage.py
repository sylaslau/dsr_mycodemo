"""Next stage (plan): Induction for Food, Post-treatment for Materials. The same section Recipe and actions shows
under "Show induction steps" / "Show post-treatment steps" (this page goes in the 5-page flow)."""

import streamlit as st

from dsr_mycodemo.app import flow, stage_ui

st.set_page_config(page_title="Next stage", page_icon="🌱", layout="wide")
flow.init()
ss = st.session_state
flow.need("choice", "Start a batch", "pages/1_Start_a_batch.py")
materials = flow.is_materials()
title, monitor_title = stage_ui.next_titles(materials)
flow.step_header(7, 8, title)

plan = ss.get("batch")
if materials:
    stage_ui.post_treatment_section(plan, flow.run())
else:
    stage_ui.induction_section(flow.sample_batch(), plan)

if st.button(f"Next: {monitor_title.lower()}", type="primary", key="next"):
    st.switch_page("pages/8_Monitor_next_stage.py")
