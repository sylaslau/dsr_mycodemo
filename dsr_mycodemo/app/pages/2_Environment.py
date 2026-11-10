import streamlit as st

from dsr_mycodemo import pipeline
from dsr_mycodemo.app import flow
from dsr_mycodemo.cultivation import baseline_guide

st.set_page_config(page_title="Environment", page_icon="📦", layout="wide")
flow.init()
ss = st.session_state
flow.need("choice", "Start a batch", "pages/1_Start_a_batch.py")
for key, value in {"env_where": None, "env_size": {}, "env_amount": {}, "env_container": None, "rh_pct": 80.0}.items():
    ss.setdefault(key, value)

# Where -> (label the pipeline plans the recipe scale from, size label, min, max, default, step)
WHERE = {
    "Plastic container": ("Small plastic container (about 1 L)", "Size (litres)", 0.5, 15.0, 1.0, 0.1),
    "Shelf or vitrine": ("Shelf or grow tent", "Size (total volume, m³)", 0.1, 2.0, 0.5, 0.1),
    "Tent or Cabinet": ("Shelf or grow tent", "Size (total volume, m³)", 0.3, 5.0, 1.0, 0.1),
    "Room or Chamber": ("Room", "Size (total volume, m³)", 5.0, 20.0, 5.0, 1.0),
}
# Shown names (the saved keys stay the same so old batches load)
WHERE_SHOWN = {"Plastic container": "Monotub or Plastic Container",
               "Shelf or vitrine": "Shelf or Vitrine"}
CONTAINERS_SHOWN = {"Grow bag": "Grow Bag"}
CONTAINERS = {
    "Glass Jar": ("Size (litres)", 0.2, 5.0, 1.0, 0.1),
    "Tupperware": ("Size (litres)", 0.2, 5.0, 1.0, 0.1),
    "Grow bag": ("Size (litres)", 0.5, 10.0, 1.0, 0.1),
    "Bucket": ("Size (litres)", 0.5, 10.0, 1.0, 0.5),
}


def size_amount(name, size_label, lo, hi, default, step, on, second=("Amount", 1)):
    """Size on the left; on the right the second field (Amount, or Layers of shelves), or none if second is None."""
    c1, c2 = st.columns(2)
    size = c1.number_input(size_label, lo, hi, ss["env_size"].get(name, default), step,
                           key=f"size_{name}", disabled=not on)
    amount = 1
    if second:
        amount = c2.number_input(second[0], 1, value=int(ss["env_amount"].get(name, second[1])), step=1,
                                 key=f"amount_{name}", disabled=not on)
    if on:
        ss["env_size"][name], ss["env_amount"][name] = size, int(amount)


flow.step_header(2, 6, "Environment")
st.write("Where do you grow them, and in what?")
where_col, cont_col = st.columns(2)

with where_col:
    st.subheader("Residence")
    for name, (label, size_label, lo, hi, default, step) in WHERE.items():
        on = ss["env_where"] == name
        if st.button(WHERE_SHOWN.get(name, name), key=f"where_{name}", type="primary" if on else "secondary", use_container_width=True):
            ss["env_where"], ss["environment"] = name, label
            ss["recipe"] = ss["batch"] = None
            st.rerun()
        size_amount(name, size_label, lo, hi, default, step, on,
                    second=None if name == "Plastic container" else ("Layers of shelves", 1))

with cont_col:
    st.subheader("Vessels")
    for name in CONTAINERS:
        on = ss["env_container"] == name
        if st.button(CONTAINERS_SHOWN.get(name, name), key=f"cont_{name}", type="primary" if on else "secondary", use_container_width=True):
            ss["env_container"] = name
            st.rerun()
        size_amount(name, *CONTAINERS[name], on)

if ss["environment"]:
    n, kg = flow.ENVIRONMENTS[ss["environment"]]
    st.caption(
        f"We plan {n} container(s) of {kg} kg dry substrate each (our default; the recipe page shows the numbers).")

st.divider()
st.header("Conditions")
st.markdown("**Input method**")
st.markdown(":green[●] Slider (active)")

t_col, h_col = st.columns(2)
temp = t_col.slider("Temperature (°C)", 10.0, 40.0,
                    ss["temp_c"] if ss["temp_c"] is not None else 21.0, 0.5)
ss["temp_c"] = float(temp)
ss["rh_pct"] = float(h_col.slider(
    "Humidity (% RH)", 20, 100, int(ss["rh_pct"]), 1))

flow.preview("Use weather data from your phone",
             "Take the ambient values from your phone.")
flow.preview("Connect an external device",
             "Read temperature and humidity from a sensor.")


row = flow.species_row()
br = pipeline.baseline_row(flow.get_batch())
if flow.is_materials():
    flow.materials_preview("Temperature check (Warnings)")
elif row is None or br is None:
    st.info(
        "No temperature range is known for this mushroom.")
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
    st.caption(f"Row used: {br[1]}.")
    if ss["goal"] == "Food":
        ft = baseline_guide.fruiting(br[0])["fruiting_temp_C"]
        st.caption(
            f"Fruiting later wants {ft['min']}–{ft['max']} °C (consensus guide).")

# Humidity check, same structure as the temperature check above
rh = ss["rh_pct"]
if flow.is_materials():
    flow.materials_preview("Humidity check (Warnings)")
elif row is None or br is None:
    st.info("No humidity value is known for this mushroom.")
else:
    target = baseline_guide.colonisation(br[0])["incubation_rh_pct"]
    status = baseline_guide.rh_status(rh, target)
    if status == "dry":
        st.warning(f"{rh:g} % RH is too dry for colonisation of {row['common_name']} (about {target} %, consensus guide).\n"
                   "The substrate surface may dry out; close the vessel or add a humidity tent.")
    elif status == "wet":
        st.warning(f"{rh:g} % RH is very wet. Water can condense on the bag or box and raise mould risk; "
                   "give some fresh air.")
    else:
        st.success(
            f"{rh:g} % RH suits colonisation of {row['common_name']} (about {target} %, consensus guide).")
    if ss["goal"] == "Food":
        fh = baseline_guide.fruiting(br[0])["fruiting_rh_pct"]
        st.caption(
            f"Fruiting later wants {fh['min']}–{fh['max']} % RH (consensus guide).")

if ss["environment"]:
    st.page_link("pages/3_Recipe_and_timeline.py",
                 label="Next: recipe and preview", icon="➡️")
else:
    st.caption("Choose where you grow to continue.")
