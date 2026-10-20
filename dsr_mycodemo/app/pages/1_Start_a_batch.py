"""Start a batch: one pick in total, a Food (mushroom) or a Thing (mycomaterial)."""

import streamlit as st

from dsr_mycodemo.app import flow
from dsr_mycodemo.cultivation import baseline_guide

st.set_page_config(page_title="What do you want to grow?",
                   page_icon="🍄", layout="wide")
flow.init()
ss = st.session_state

# shown name -> consensus-table common name
FOODS = {"Pearl or Blue Oyster": "Pearl Oyster", "King Oyster": "King Oyster", "Shiitake": "Shiitake",
         "Lion's mane": "Lion's Mane", "Enoki": "Enoki"}
THINGS = ["Packaging foam", "Acoustic panel",
          "Mycoleather", "Bricks or blocks", "Game pieces"]
FOOD_OWN, THING_OWN = "Your next culinary invention", "Your next thingiverse invention"
SPECIES_BY_COMMON_NAME = {s["common_name"]: s["species"] for s in baseline_guide.species_list()}
FOOD_SPECIES = {shown: SPECIES_BY_COMMON_NAME[common_name] for shown, common_name in FOODS.items()}


def pick(goal, choice, custom_name=""):
    """Save the one pick the way the old Start and What to grow pages did; a new pick resets the recipe."""
    ss["goal"], ss["choice"], ss["custom_name"] = goal, choice, custom_name
    ss["recipe"] = ss["batch"] = None
    st.rerun()


def is_food(shown):
    return ss["goal"] == "Food" and ss["choice"] == FOOD_SPECIES[shown]


st.title("Start a batch")
st.write("What do you want to grow? Pick one for this batch.")
left, right = st.columns(2)

with left:
    st.subheader("Food")
    for shown in FOODS:
        on = is_food(shown)
        if st.button(shown, key=f"food_{shown}", type="primary" if on else "secondary", use_container_width=True):
            pick("Food", FOOD_SPECIES[shown])
        if on:
            st.caption(f"*{FOOD_SPECIES[shown]}*")
    own = ss["goal"] == "Food" and ss["choice"] == "Custom" and ss["custom_name"] not in FOODS
    if st.button(FOOD_OWN, key="food_own", type="primary" if own else "secondary", use_container_width=True):
        pick("Food", "Custom", "")
    if own:
        name = st.text_input("What is it called?",
                             value=ss["custom_name"], key="food_own_in")
        ss["custom_name"] = name.strip()
        st.caption("For your own mushroom we have no temperature range or recipe figures; "
                   "try identification tools to get some reference; "
                   "I'll help you track with the experimental conditions.")

with right:
    st.subheader("Things")
    for p in THINGS:
        on = ss["goal"] == "Materials" and ss["choice"] == p
        if st.button(p, key=f"thing_{p}", type="primary" if on else "secondary", use_container_width=True):
            pick("Materials", p)
    own = ss["goal"] == "Materials" and ss["choice"] not in THINGS
    if st.button(THING_OWN, key="thing_own", type="primary" if own else "secondary", use_container_width=True):
        pick("Materials", "Your own invention", "")
    if own:
        name = st.text_input("What is it called?",
                             value=ss["custom_name"], key="thing_own_in")
        ss["custom_name"] = name.strip()
        ss["choice"] = name.strip() or "Your own invention"


if ss["choice"]:
    st.success(f"Chosen: {flow.choice_label()}")
    st.page_link("pages/2_Environment.py",
                 label="Next: your environment", icon="➡️")
