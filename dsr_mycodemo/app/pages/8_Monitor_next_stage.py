"""Monitor next stage: Monitor fruiting (Food) or Monitor post-treatment (Materials). The reading box of the
residence chosen on page 7, then one record per sample."""

import streamlit as st

from dsr_mycodemo import pipeline
from dsr_mycodemo.app import flow, stage_ui

st.set_page_config(page_title="Monitor next stage", page_icon="📷", layout="wide")
flow.init()
ss = st.session_state
flow.need("choice", "Start a batch", "pages/1_Start_a_batch.py")
materials = flow.is_materials()
plan_title, title = stage_ui.next_titles(materials)
flow.step_header(8, 8, title)

plan = ss.get("batch")
batch = flow.sample_batch()
residence = stage_ui.chosen_residence("next")
if residence is None:
    st.info(f"Choose the residence on {plan_title} first.")
    if st.button(f"Open {plan_title}", key="to_next_plan"):
        st.switch_page("pages/7_Next_stage.py")
    st.stop()

ranges = pipeline.next_stage_ranges(batch)
fields = ("temp", "rh") if materials else ("temp", "rh", "co2")
with st.container(border=True):
    st.subheader(stage_ui.residence_label(residence))
    if materials:
        st.caption("Temperature and humidity are a record only: our data has no wanted ranges for post-treatment, "
                   "so the lights stay yellow.")
    elif ranges is None:
        st.caption("No fruiting ranges are known for this mushroom.")
    elif not materials:
        st.caption("Lights: fruiting ranges of the consensus guide.")
    stage_ui.environment_log("next", residence, ranges, batch.inoc_date if plan else None, kind="next", fields=fields)

if not plan:
    st.info("Save a plan on Recipe and timeline to keep a record per sample.")
    if st.button("Open Recipe and timeline", key="to_recipe"):
        st.switch_page("pages/3_Recipe_and_timeline.py")
    st.stop()

sample = st.selectbox("Sample (one bag, jar or mould)", stage_ui.plan_samples(plan), key="next_sample")
with st.container(border=True):
    st.markdown(f"**{sample}**")
    stage_ui.sample_log("next", sample, plan["inoc_date"], materials=materials)
