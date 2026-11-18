"""Shared pieces for the stage pages (Environment, Recipe and timeline, Next stage, Monitor next stage).

Words: residence = the space (box, tent, room, oven); container = a box or crate inside the residence (Materials);
vessel = what holds the substrate (jar, bag, mould).

Saved session keys: env_where (colonisation residence), env_size / env_amount ({name: value}), env_container
(vessel), env_box (container, Materials, optional); residences {"colonisation": ..., "next": ...};
env_size_next / env_amount_next for the next-stage residence.
"""

import streamlit as st

from dsr_mycodemo import pipeline

# residence -> (recipe-scale label for the pipeline or None, size spec); size spec = (size label, min, max, default,
# step, second field (label, default) or None), or None for no size fields
RESIDENCES = {
    "Plastic container": ("Small plastic container (about 1 L)",
                          ("Size (litres)", 0.5, 15.0, 1.0, 0.1, None)),
    "Shelf or vitrine": ("Shelf or grow tent", ("Size (total volume, m³)", 0.1, 2.0, 0.5, 0.1, ("Layers of shelves", 1))),
    "Tent or Cabinet": ("Shelf or grow tent", ("Size (total volume, m³)", 0.3, 5.0, 1.0, 0.1, ("Layers of shelves", 1))),
    "Room or Chamber": ("Room", ("Size (total volume, m³)", 5.0, 20.0, 5.0, 1.0, ("Layers of shelves", 1))),
}
# Materials after colonisation (post-treatment): oven, drying rack or room, press
RESIDENCES_POST = {
    "Oven": (None, ("Size (litres)", 10.0, 200.0, 50.0, 5.0, None)),
    "Drying rack or room": (None, ("Size (total volume, m³)", 0.1, 50.0, 1.0, 0.1, ("Layers of shelves", 1))),
    "Press": (None, None),
}
# shown names (the saved keys stay the same so old batches load)
SHOWN = {"Plastic container": "Monotub or Plastic Container", "Shelf or vitrine": "Shelf or Vitrine",
         "Grow bag": "Grow Bag"}
# vessels (hold the substrate): name -> (size label, min, max, default, step)
FOOD_VESSELS = {
    "Glass Jar": ("Size (litres)", 0.2, 5.0, 1.0, 0.1),
    "Tupperware": ("Size (litres)", 0.2, 5.0, 1.0, 0.1),
    "Grow bag": ("Size (litres)", 0.5, 10.0, 1.0, 0.1),
    "Bucket": ("Size (litres)", 0.5, 10.0, 1.0, 0.5),
}
MATERIAL_VESSELS = {
    "Mould (box)": ("Size (litres)", 0.1, 10.0, 1.0, 0.1),
    "Mould (cylinder)": ("Size (litres)", 0.1, 10.0, 1.0, 0.1),
    "Grow bag": ("Size (litres)", 0.5, 10.0, 1.0, 0.1),
}
ALL_VESSELS = list(dict.fromkeys([*FOOD_VESSELS, *MATERIAL_VESSELS]))
# containers inside the residence (Materials, optional): name -> (compartment.csv container_type, size spec).
# Default litres from compartment.csv: micro box 185 x 185 x 78 mm (C-007), EURO crate 60 x 40 x 18.5 cm (C-012),
# 4 L filter bag (C-014)
CONTAINERS = {
    "Micro box": ("micro_box", ("Size (litres)", 0.5, 10.0, 2.7, 0.1)),
    "Crate": ("crate", ("Size (litres)", 5.0, 100.0, 44.0, 1.0)),
    "Filter bag": ("bag", ("Size (litres)", 0.5, 10.0, 4.0, 0.5)),
}
STAGE_KEYS = ("colonisation", "next")


def _ss():
    ss = st.session_state
    for key, value in {"env_where": None, "env_size": {}, "env_amount": {}, "env_container": None, "env_box": None,
                       "residences": {}, "env_size_next": {}, "env_amount_next": {}}.items():
        ss.setdefault(key, value)
    return ss


def residence_options(stage_key, materials=None):
    """The residences offered for a stage: the growing spaces for colonisation (both modes) and for Food's next stage;
    oven, drying rack or room and press for Materials' next stage (post-treatment)."""
    if stage_key not in STAGE_KEYS:
        raise ValueError(f"unknown stage key {stage_key!r}")
    materials = (st.session_state.get("goal") == "Materials") if materials is None else materials
    return RESIDENCES_POST if (stage_key == "next" and materials) else RESIDENCES


def chosen_residence(stage_key):
    """The residence saved for this stage; 'next' falls back to the colonisation one (env_where) when it is empty or
    not offered for the mode (as pipeline.residence does for a batch)."""
    ss = _ss()
    if stage_key == "colonisation":
        return ss["env_where"]
    nxt = ss["residences"].get("next")
    return nxt if nxt in residence_options("next") else ss["env_where"]


def size_amount(name, spec, on, sizes="env_size", amounts="env_amount", prefix=""):
    """Size on the left; on the right the second field (Amount, or Layers of shelves), or none.
    spec = (size label, min, max, default, step[, second]) where second = (label, default) or None; a 5-item spec has
    Amount as its second field (vessels and containers)."""
    ss = _ss()
    size_label, lo, hi, default, step, *rest = spec
    second = rest[0] if rest else ("Amount", 1)
    c1, c2 = st.columns(2)
    size = c1.number_input(size_label, lo, hi, float(ss[sizes].get(name, default)), step,
                           key=f"{prefix}size_{name}", disabled=not on)
    amount = 1
    if second:
        amount = c2.number_input(second[0], 1, value=int(ss[amounts].get(name, second[1])), step=1,
                                 key=f"{prefix}amount_{name}", disabled=not on)
    if on:
        ss[sizes][name], ss[amounts][name] = size, int(amount)


def residence_picker(stage_key):
    """The Residence box: one button per residence with its size fields. Saves the choice per stage in
    ss['residences'][stage_key]; colonisation also keeps the old keys (env_where, environment = recipe scale) and
    clears the plan, as the Environment page always did. Returns the chosen residence or None."""
    ss = _ss()
    options = residence_options(stage_key)
    nxt = stage_key == "next"
    sizes, amounts, prefix = ("env_size_next", "env_amount_next", "next_") if nxt else ("env_size", "env_amount", "")
    current = ss["residences"].get("next") if nxt else ss["env_where"]
    st.subheader("Residence")
    for name, (label, spec) in options.items():
        on = current == name
        if st.button(SHOWN.get(name, name), key=f"{prefix}where_{name}", type="primary" if on else "secondary",
                     use_container_width=True):
            ss["residences"] = {**ss["residences"], stage_key: name}
            if not nxt:
                ss["env_where"], ss["environment"] = name, label
                ss["recipe"] = ss["batch"] = None
            st.rerun()
        if spec is not None:
            size_amount(name, spec, on, sizes, amounts, prefix)
    return current if current in options else None


def item_picker(title, items, key, button_prefix, optional=False, shown=SHOWN):
    """A column of buttons (vessels or containers) with Size and Amount each; saves the choice in ss[key].
    optional: a second click on the chosen one clears it."""
    ss = _ss()
    st.subheader(title)
    for name, spec in items.items():
        on = ss[key] == name
        if st.button(shown.get(name, name), key=f"{button_prefix}_{name}", type="primary" if on else "secondary",
                     use_container_width=True):
            ss[key] = None if (optional and on) else name
            st.rerun()
        size_amount(name, spec, on)


def vessels_for(materials):
    return MATERIAL_VESSELS if materials else FOOD_VESSELS


def residence_label(name):
    return SHOWN.get(name, name) if name else "not chosen"

