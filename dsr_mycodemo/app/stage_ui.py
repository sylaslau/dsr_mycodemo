"""Shared pieces for the stage pages (Environment, Recipe and timeline, Next stage, Monitor next stage).

Words: residence = the space (box, tent, room, oven); container = a box or crate inside the residence (Materials);
vessel = what holds the substrate (jar, bag, mould).

Saved session keys: env_where (colonisation residence), env_size / env_amount ({name: value}), env_container
(vessel), env_box (container, Materials, optional); residences {"colonisation": ..., "next": ...};
env_size_next / env_amount_next for the next-stage residence.
"""

from datetime import date, datetime
import html

import streamlit as st

from dsr_mycodemo import pipeline
from dsr_mycodemo.app import flow
from dsr_mycodemo.cultivation import baseline_guide as bg

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
                       "residences": {}, "env_size_next": {}, "env_amount_next": {}, "monitor_env": {},
                       "monitor_env_next": {}, "outcomes": {}, "harvest": {}, "next_photos": {}, "weights": {}}.items():
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



# --- stage bubbles (moved from Recipe and timeline) --------------------------------------------
EVENT_COLOR, STAGE_COLOR = "#8A5A3B", "#5E6B3A"
NOT_IN_GUIDE = "not in guide"
STAGE_CARDS = ("Inoculation", "Colonising", "Induction", "Fruiting", "Harvest")


def _val(x, unit="", before=""):
    return NOT_IN_GUIDE if str(x) in ("", "nan", "None") else f"{before}{x:g}{unit}"


def _rng(lo, hi, unit):
    if str(lo) == "nan" or str(hi) == "nan":
        return NOT_IN_GUIDE
    return f"{lo:g}–{hi:g}{unit}" if lo != hi else f"{lo:g}{unit}"


def stage_cards(r, names=STAGE_CARDS):
    """One row of stage bubbles for a consensus-guide row r: name · days, then temperature, humidity, CO2, light.
    names picks the bubbles (Inoculation, Colonising, Induction, Fruiting, Harvest) in that order."""
    tl = bg.stages(r).set_index("stage")
    col_days = bg.colonisation(r)["colonisation_days"]
    ind_row, har_row = tl.loc["Start induction"], tl.loc["First harvest"]

    def span(label):
        s_ = tl.loc[label]
        return f"day {s_['start_day']}–{s_['end_day']} (typical {s_['typical_day']})"

    inc_c = (_rng(r["incubation_temp_min_C"], r["incubation_temp_max_C"], " °C"),
             _val(r["incubation_RH_pct"], " %", ">"), "high CO2 fine (closed)", "not required")
    fr_c = (_rng(r["fruiting_temp_min_C"], r["fruiting_temp_max_C"], " °C"),
            _rng(r["fruiting_RH_min_pct"], r["fruiting_RH_max_pct"], " %"),
            _val(r["fruiting_CO2_max_ppm"], " ppm", "< "), "500-1000 lux")
    bubbles = {"Inoculation": (EVENT_COLOR, "day 0", inc_c),
               "Colonising": (STAGE_COLOR, f"day {col_days['min']}–{col_days['max']} (typical {col_days['typical']})",
                              inc_c),
               "Induction": (EVENT_COLOR, span("Start induction"), fr_c),
               "Fruiting": (STAGE_COLOR, (f"day {ind_row['start_day']}–{har_row['end_day']} "
                                          f"(typical {ind_row['typical_day']:g}–{har_row['typical_day']:g})"), fr_c),
               "Harvest": (EVENT_COLOR, span("First harvest"), fr_c)}
    shown = [n for n in STAGE_CARDS if n in names]
    for box, name in zip(st.columns(len(shown)), shown):
        color, when, (tmp, rh, co2, lt) = bubbles[name]
        body = (f"<b>{html.escape(name)}</b> · {html.escape(when)}<br>🌡️ {html.escape(tmp)}<br>💧 {html.escape(rh)}"
                f"<br>🌬️ {html.escape(co2)}<br>💡 {html.escape(lt)}")
        box.markdown(f"<div style='border:2px solid {color}; border-left:8px solid {color}; border-radius:8px; "
                     f"padding:0.6rem 0.8rem; margin:0.4rem 0; height:100%;'>{body}</div>", unsafe_allow_html=True)


# --- traffic lights (moved from Monitor) --------------------------------------------------------
LIGHTS = {"green": "#B4BC44", "red": "#F12430", "yellow": "#FFBF00", "grey": "#9E9E9E"}
# reading key -> (icon, label, unit, step, format)
READING_FIELDS = {"temp": ("🌡️", "Temperature", "°C", 0.5, "%.1f"), "rh": ("💧", "Humidity", "%", 1.0, "%.0f"),
                  "co2": ("🫧", "CO2", "ppm", 100.0, "%.0f")}
# stage -> (session store {residence: latest entry + "log"}, widget key prefix); colonisation = Monitor's own keys
READING_STORES = {"colonisation": ("monitor_env", "mon_"), "next": ("monitor_env_next", "next_mon_")}


def light(value, rng):
    """green in range, red out of range, yellow when not entered or no range is known."""
    if value is None or rng is None:
        return "yellow"
    return "green" if rng[0] <= value <= rng[1] else "red"


def worst(colours):
    """Worst light of a residence; grey (marked unknown) does not count."""
    colours = [c for c in colours if c != "grey"]
    return "red" if "red" in colours else "yellow" if "yellow" in colours else "green"


def dot(colour):
    return f'<span style="color:{LIGHTS[colour]}">●</span>'


def bubble(colour, icon, label, text):
    return (f'<div style="background:{LIGHTS[colour]}22;border:2px solid {LIGHTS[colour]};border-radius:999px;'
            f'padding:0.2rem 0.9rem;margin-bottom:0.3rem;display:inline-block">{icon} <b>{label}</b> {text}</div>')


def _range(ranges, key):
    return ranges[key][:2] if ranges and key in ranges else None


def environment_log(stage, residence, ranges, inoc_date=None, kind="grow", fields=("temp", "rh", "co2")):
    """The reading box of one residence for a stage ('colonisation' = Monitor, 'next' = Monitor next stage): one
    input per field with its traffic light against ranges ({key: (lo, hi, prefill)} or None), Measured by, date,
    time and Save. Returns (worst light, the entry saved on this run or None)."""
    ss = _ss()
    store, p = READING_STORES[stage]
    saved = ss[store].setdefault(residence, {})
    values, colours, co2_unknown = {}, [], False
    for col, key in zip(st.columns(len(fields)), fields):
        icon, label, unit, step, fmt = READING_FIELDS[key]
        holder = col.empty()
        default = float(ranges[key][2]) if ranges and key in ranges else None
        unknown = key == "co2" and ss.get(f"{p}co2_unknown_{residence}", False)
        values[key] = col.number_input(f"{label} ({unit})", value=default, step=step, format=fmt,
                                       key=f"{p}{key}_{residence}_{kind}", label_visibility="collapsed",
                                       disabled=unknown)
        if key == "co2":
            co2_unknown = col.checkbox("CO2 unknown", key=f"{p}co2_unknown_{residence}")
        colour = "grey" if unknown else light(values[key], _range(ranges, key))
        colours.append(colour)
        holder.markdown(bubble(colour, icon, label, "unknown" if unknown else
                               "not entered" if values[key] is None else f"{values[key]:g} {unit}"),
                        unsafe_allow_html=True)
    m_col, d_col, t_col, s_col = st.columns([2, 1, 1, 1], vertical_alignment="bottom")
    measured = m_col.selectbox("Measured by", pipeline.MEASURED_BY, index=2, key=f"{p}by_{residence}")
    on_day = d_col.date_input("Date", date.today(), key=f"{p}date_{residence}")
    at_time = t_col.time_input("Time", "now", key=f"{p}time_{residence}")
    entry = None
    if s_col.button("Save", key=f"{p}save_{residence}", use_container_width=True):
        entry = pipeline.reading_entry(values, measured, datetime.combine(on_day, at_time), inoc_date, co2_unknown)
        saved.update(entry)
        saved.setdefault("log", []).append(entry)
        st.success(f"Saved for {entry['datetime'].replace('T', ' ')}"
                   + (f" (day {entry['day']} since inoculation)." if entry["day"] is not None else "."))
    return worst(colours), entry


def latest_reading(stage, residence):
    """The latest saved reading for a residence at a stage; 'next' falls back to Monitor's reading of the same
    residence (a batch that stays where it colonised). {} when nothing is saved."""
    ss = _ss()
    found = {k: v for k, v in ss["monitor_env_next"].get(residence, {}).items() if k != "log"} if stage == "next" else {}
    if not found:
        found = {k: v for k, v in ss["monitor_env"].get(residence, {}).items() if k != "log"}
    return found


def conditions_check(ranges, reading, fields=("temp", "rh", "co2")):
    """Bubbles: each wanted range against the reading (green inside, red outside, yellow not entered). Returns the
    worst light."""
    colours = []
    for col, key in zip(st.columns(len(fields)), fields):
        icon, label, unit, *_ = READING_FIELDS[key]
        value, rng = reading.get(key), _range(ranges, key)
        colour = light(value, rng)
        colours.append(colour)
        want = f"wanted {rng[0]:g}–{rng[1]:g} {unit}" if rng else "no range known"
        now = "not entered" if value is None else f"{value:g} {unit}"
        col.markdown(bubble(colour, icon, label, f"{now} ({want})"), unsafe_allow_html=True)
    return worst(colours)


# --- per-sample records ---------------------------------------------------------------------------
def colonised_date(prefix=None):
    """(latest 'Fully colonised on' date typed on Monitor, number typed) over the samples whose ID starts with
    prefix (the batch label); (None, 0) when none is typed."""
    typed = [o["colonised"] for s, o in _ss()["outcomes"].items()
             if o.get("colonised") and (prefix is None or str(s).startswith(prefix))]
    return (max(typed), len(typed)) if typed else (None, 0)


def _flush_record(sample, inoc_date, p=""):
    harvest = _ss()["harvest"]
    st.markdown("**Harvest**")
    h1, h2, h3 = st.columns([2, 2, 1], vertical_alignment="bottom")
    when = h1.date_input("Harvest date", date.today(), min_value=inoc_date, key=f"{p}h_date_{sample}")
    grams = h2.number_input("Fresh weight (g)", 0.0, step=10.0, key=f"{p}h_g_{sample}")
    if h3.button("Add flush", key=f"{p}h_add_{sample}", disabled=grams <= 0, use_container_width=True):
        harvest.setdefault(sample, []).append({"date": when, "g": float(grams)})
    for k, f in enumerate(harvest.get(sample, []), start=1):
        st.caption(f"Flush {k}: {f['date']:%Y-%m-%d}, {f['g']:g} g fresh")


def photo_record(sample, label="Photo of this sample"):
    """Photo upload kept as a record only (no analysis): {date, file, data} in ss['next_photos'][sample]."""
    rows = _ss()["next_photos"].setdefault(sample, [])
    up = st.file_uploader(label, type=["jpg", "jpeg", "png"], key=f"next_photo_{sample}")
    if up is not None and not any(r["file"] == up.name for r in rows):
        rows.append({"date": date.today().isoformat(), "file": up.name, "data": up.getvalue()})
    if rows:
        st.caption(f"{len(rows)} photo(s) recorded for {sample}: " + ", ".join(r["file"] for r in rows))
    return rows


DRY_RULE = (f"Project rule, not a model: a sample counts as **dry** when its weight changes by under "
            f"{pipeline.DRY_LIMIT_PCT:g} % per day for {pipeline.DRY_READINGS} readings in a row.")


def weight_log(sample):
    """Weight log of one sample (date, grams) in ss['weights'][sample], with the % change per day and the dry check."""
    log = _ss()["weights"].setdefault(sample, [])
    st.markdown("**Weight**")
    w1, w2, w3 = st.columns([2, 2, 1], vertical_alignment="bottom")
    when = w1.date_input("Date", date.today(), key=f"w_date_{sample}")
    grams = w2.number_input("Weight (g)", 0.0, step=1.0, key=f"w_g_{sample}")
    if w3.button("Add weight", key=f"w_add_{sample}", disabled=grams <= 0, use_container_width=True):
        log.append({"date": when, "g": float(grams)})
    for r in pipeline.weight_changes(log):
        change = "" if r["pct_per_day"] is None else f", {r['pct_per_day']:+.1f} % per day"
        st.caption(f"{r['date']:%Y-%m-%d}: {r['g']:g} g{change}")
    if pipeline.is_dry(log):
        st.success(f"{sample} is dry: the weight has stopped dropping.")
    elif log:
        st.info(f"{sample} is not dry yet: keep weighing.")
    st.caption(DRY_RULE)
    return log


def sample_log(stage, sample, inoc_date, materials=False):
    """The record of one sample at a stage. 'colonisation' (Monitor): fully colonised date, mould seen and, for Food,
    the harvest flushes. 'next' (Monitor next stage): Food = photo (record only) and the flushes; Materials = weight
    log with the dry check and a photo (record only)."""
    ss = _ss()
    if stage == "colonisation":
        out = ss["outcomes"].setdefault(sample, {"colonised": None, "mould": False})
        with st.expander(f"Record for {sample}"):
            c1, c2 = st.columns(2, vertical_alignment="bottom")
            out["colonised"] = c1.date_input("Fully colonised on", value=out["colonised"], min_value=inoc_date,
                                             key=f"o_col_{sample}", help="Leave empty while it is still colonising.")
            out["mould"] = c2.checkbox("Mould seen", value=out["mould"], key=f"o_mould_{sample}")
            if not materials:
                _flush_record(sample, inoc_date)
        return
    if stage != "next":
        raise ValueError(f"unknown stage {stage!r}")
    if materials:
        weight_log(sample)
        photo_record(sample)
        return
    rows = photo_record(sample)
    ready = pipeline.harvest_readiness([r["file"] for r in rows])
    flow.preview("Harvest readiness", f"Planned: photos tell you young or ready to pick ({ready['n_photos']} "
                 "photo(s) so far). The model is still in training; use the harvest dates until then.")
    _flush_record(sample, inoc_date, p="next_")


# --- next-stage pages (7 and 8) ---------------------------------------------------------------------
# mode -> (page 7 title, page 8 title)
NEXT_TITLES = {False: ("Induction", "Monitor fruiting"), True: ("Post-treatment", "Monitor post-treatment")}


def next_titles(materials):
    return NEXT_TITLES[bool(materials)]


def plan_samples(plan):
    """Sample IDs of the saved plan ('<label>-01' ...), as Monitor names them; [] without a plan."""
    if not plan:
        return []
    return [f"{plan['batch_label']}-{i:02d}" for i in range(1, int(plan["n_containers"]) + 1)]
