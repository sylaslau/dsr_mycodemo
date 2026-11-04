"""Mycelly app: welcome page (the entry file).

Run from the project folder (with the .venv active):
    streamlit run dsr_mycodemo/app/Welcome.py
"""

import streamlit as st

from dsr_mycodemo import collect, pipeline
from dsr_mycodemo.app import flow

st.set_page_config(page_title="Mycelly", page_icon="🍄", layout="wide")
flow.init()


def stage_flow(title, stages):
    """One vertical flow: boxes top to bottom with a down arrow between; (name, active) pairs."""
    parts = [f"<h3>{title}</h3>"]
    for i, (name, active) in enumerate(stages):
        if i:
            parts.append('<div class="sf-arrow">↓</div>')
        parts.append(
            f'<div class="sf-box{"" if active else " off"}">{name}</div>')
    return "".join(parts)


st.title("Mycelly")
st.markdown(
    "<div style='font-size:1.05rem'>Your mycelium cultivation buddy 🍄 I sit by your side to:"
    "<ul>"
    "<li>🍄 guide you through you a starter recipe </li>"
    "<li>📷 watch out for your mycelium and help you tend to their needs </li>"
    "<li>⏰ tell you when the next stage is coming and how to proceed</li>"
    "</ul></div>",
    unsafe_allow_html=True,
)

food, thing = st.columns(2)
food.markdown(stage_flow("Food", [("Culture", False), ("Spawn", False), ("Block", True),
                                  ("Flushes", True)]), unsafe_allow_html=True)
materials_on = pipeline.materials_mode() != "off"
thing.markdown(stage_flow("Thing", [("Culture", False), ("Spawn", False), ("Pre-treatment", False),
                                    ("Block", materials_on), ("Post-treatment", False)]), unsafe_allow_html=True)
if not materials_on:
    with thing:
        flow.preview("Materials", "Switched off in this version: only Food runs.")

with st.expander("What we collect"):
    st.write("Only if you tick the box on Monitor and press Send: " + collect.SHARE_TEXT)

st.write("")
st.caption("")
