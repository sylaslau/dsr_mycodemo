"""Mycelly app: welcome page (the entry file).

Run from the project folder (with the .venv active):
    streamlit run dsr_mycodemo/app/Welcome.py
"""

from pathlib import Path

import streamlit as st

from dsr_mycodemo.app import flow

IMAGES = Path(__file__).parent / "images"

st.set_page_config(page_title="Mycelly", page_icon="🍄", layout="wide")
flow.init()


st.title("Mycelly")
st.image(str(IMAGES / "shroom.png"), width=100)
st.markdown(
    "<div style='font-size:1.05rem'>Your mycelium cultivation buddy 🍄 I sit by your side to:"
    "<ul>"
    "<li>🍄 guide you through you a starter recipe </li>"
    "<li>📷 watch out for your mycelium and help you tend to their needs </li>"
    "<li>⏰ tell you when the next stage is coming and how to proceed</li>"
    "</ul></div>",
    unsafe_allow_html=True,
)

st.image(str(IMAGES / "app_overview.png"), width="stretch")

st.subheader("Data collection")
st.markdown("We do not collect any personal data.")
st.markdown("We collect data directly related to mycelium cultivation to improve how Mycelly assists. \n"
            "Examples: environmental conditions, growing parameters and photos, and product results.")
