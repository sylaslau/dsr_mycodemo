import streamlit as st

from dsr_mycodemo import pipeline
from dsr_mycodemo.app import flow, stage_ui
from dsr_mycodemo.cultivation import baseline_guide

st.set_page_config(page_title="Environment", page_icon="📦", layout="wide")
flow.init()
ss = st.session_state
flow.need("choice", "Start a batch", "pages/1_Start_a_batch.py")
ss.setdefault("rh_pct", 80.0)

flow.step_header(2, 8, "Environment")
materials = flow.is_materials()
st.write("Where do you grow them, and in what?")
if materials:      # Materials: residence, then the optional container inside it, then the vessel (mould or bag)
    where_col, box_col, cont_col = st.columns(3)
    with box_col:
        stage_ui.item_picker("Containers", {k: v[1] for k, v in stage_ui.CONTAINERS.items()}, "env_box", "box",
                             optional=True)
        st.caption("Optional: a box, crate or filter bag inside the residence. Click again to clear.")
else:
    where_col, cont_col = st.columns(2)

with where_col:
    stage_ui.residence_picker("colonisation")

with cont_col:
    stage_ui.item_picker("Vessels", stage_ui.vessels_for(materials), "env_container", "cont")

st.divider()
st.header("Conditions")
st.markdown("**Input method**")
st.markdown(":green[●] Slider (active)")

t_col, h_col = st.columns(2)
row = flow.species_row()
br = pipeline.baseline_row(flow.get_batch())

with t_col:
    temp = st.slider("Temperature (°C)", 10.0, 40.0,
                     ss["temp_c"] if ss["temp_c"] is not None else 21.0, 0.5)
    ss["temp_c"] = float(temp)
    if flow.is_materials():
        flow.materials_preview("Temperature check (Warnings)")
    elif row is None or br is None:
        st.info("No temperature range is known for this mushroom.")
    else:
        inc = baseline_guide.colonisation(br[0])["incubation_temp_C"]
        lo, hi = inc["min"], inc["max"]
        if lo <= temp <= hi:
            st.success(
                f"{temp:g} °C is inside the colonisation range of {row['common_name']} ({lo}–{hi} °C, consensus guide).")
        elif temp > hi:
            st.warning(f"{temp:g} °C is too hot for {row['common_name']} ({lo}–{hi} °C, consensus guide).\n"
                       "The mycelium may be stressed or die back; consider a cooler spot.")
        else:
            st.warning(f"{temp:g} °C is too cold for {row['common_name']} ({lo}–{hi} °C, consensus guide).\n"
                       "\n Colonisation will be slower, or may stall; consider a warmer spot.")

with h_col:
    rh = ss["rh_pct"] = float(st.slider("Humidity (% RH)", 20, 100, int(ss["rh_pct"]), 1))
    if flow.is_materials():
        flow.materials_preview("Humidity check (Warnings)")
    elif row is None or br is None:
        st.info("No humidity value is known for this mushroom.")
    else:
        target = baseline_guide.colonisation(br[0])["incubation_rh_pct"]
        status = baseline_guide.rh_status(rh, target)
        if status == "dry":
            st.warning(f"{rh:g} % RH is too dry for colonisation of {row['common_name']} (about {target} %, "
                       "consensus guide).\nThe substrate surface may dry out; close the vessel or add a humidity tent.")
        elif status == "wet":
            st.warning(f"{rh:g} % RH is very wet. Water can condense on the bag or box and raise mould risk; "
                       "give some fresh air.")
        else:
            st.success(
                f"{rh:g} % RH suits colonisation of {row['common_name']} (about {target} %, consensus guide).")

flow.preview("Use weather data from your phone",
             "Take the ambient values from your phone.")
flow.preview("Connect an external device",
             "Read temperature and humidity from a sensor.")

if ss["environment"]:
    if st.button("Next: recipe and preview", type="primary", key="next"):
        st.switch_page("pages/3_Recipe_and_timeline.py")
else:
    st.caption("Choose where you grow to continue.")
