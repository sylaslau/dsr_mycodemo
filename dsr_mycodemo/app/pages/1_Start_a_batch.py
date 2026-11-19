import streamlit as st

from dsr_mycodemo import pipeline
from dsr_mycodemo.app import flow, stage_ui
from dsr_mycodemo.cultivation import baseline_guide

st.set_page_config(page_title="Start a batch", page_icon="🍄", layout="wide")
flow.init()
ss = st.session_state

# shown name -> consensus-table common name
FOODS = {"Pearl or Blue Oyster": "Pearl Oyster", "King Oyster": "King Oyster", "Shiitake": "Shiitake",
         "Lion's mane": "Lion's Mane", "Enoki": "Enoki"}
THINGS = ["Packaging foam", "Acoustic panel",
          "Bricks or blocks", "Game pieces"]
FOOD_OWN, THING_OWN = "Another Mushroom", "Your next thingiverse invention"
SPECIES_BY_COMMON_NAME = {s["common_name"]: s["species"]
                          for s in baseline_guide.species_list()}
FOOD_SPECIES = {shown: SPECIES_BY_COMMON_NAME[common_name]
                for shown, common_name in FOODS.items()}


def pick(goal, choice, custom_name=""):
    ss["goal"], ss["choice"], ss["custom_name"] = goal, choice, custom_name
    ss["recipe"] = ss["batch"] = None
    for k in ("batch_stage", "next_start"):
        ss.pop(k, None)
    st.rerun()


def is_food(shown):
    return ss["goal"] == "Food" and ss["choice"] == FOOD_SPECIES[shown]


flow.header("Start a batch")
st.header("Step 1. Pick what you want to grow")
left, right = st.columns(2)

with left:
    st.subheader("Mushrooms for Food")
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
    st.subheader("Materials or Things")
    materials_off = pipeline.materials_mode() == "off"
    if materials_off:
        flow.preview(
            "Materials", "Switched off in this version: only Food runs.")
    for p in THINGS:
        on = ss["goal"] == "Materials" and ss["choice"] == p
        if st.button(p, key=f"thing_{p}", type="primary" if on else "secondary", use_container_width=True,
                     disabled=materials_off):
            pick("Materials", p)
    own = ss["goal"] == "Materials" and ss["choice"] not in THINGS
    if st.button(THING_OWN, key="thing_own", type="primary" if own else "secondary", use_container_width=True,
                 disabled=materials_off):
        pick("Materials", "Your own invention", "")
    if ss["goal"] == "Materials" and not materials_off:
        ss["material_species"] = st.radio(
            "Fungus", pipeline.MATERIAL_SPECIES, horizontal=True, key="material_species_in",
            label_visibility="collapsed",
            index=pipeline.MATERIAL_SPECIES.index(ss["material_species"])
            if ss["material_species"] in pipeline.MATERIAL_SPECIES else 0)
    if own and not materials_off:
        name = st.text_input("What is it called?",
                             value=ss["custom_name"], key="thing_own_in")
        ss["custom_name"] = name.strip()
        ss["choice"] = name.strip() or "Your own invention"


if ss["goal"] == "Materials" and pipeline.materials_mode() == "off":
    st.info("Materials are switched off in this version; pick a Food to continue.")
elif ss["choice"]:
    st.success(f"Chosen: {flow.choice_label()}"
               + (f" ({ss['material_species']})" if ss["goal"] == "Materials" else ""))
    st.divider()
    stage_ui.environment_section()
    if ss["environment"]:
        if st.button("Next: recipe and actions", type="primary", key="next"):
            st.switch_page("pages/2_Recipe_and_actions.py")
    else:
        st.caption("Choose where you grow to continue.")
