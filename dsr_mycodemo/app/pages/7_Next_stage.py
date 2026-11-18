"""Next stage (plan): Induction for Food, Post-treatment for Materials. Start date, the residence chosen again,
what to do, the conditions check and the dates."""

import streamlit as st

from dsr_mycodemo import pipeline
from dsr_mycodemo.app import flow, stage_ui
from dsr_mycodemo.cultivation import baseline_guide as bg

st.set_page_config(page_title="Next stage", page_icon="🌱", layout="wide")
flow.init()
ss = st.session_state
flow.need("choice", "Start a batch", "pages/1_Start_a_batch.py")
materials = flow.is_materials()
title, monitor_title = stage_ui.next_titles(materials)
flow.step_header(7, 8, title)

plan = ss.get("batch")
batch = flow.sample_batch()
typed, n_typed = stage_ui.colonised_date(plan["batch_label"] if plan else None)


def residence_section(help_text):
    where_col, note_col = st.columns(2)
    with where_col:
        stage_ui.residence_picker("next")
    with note_col:
        st.subheader("Colonised in")
        st.write(stage_ui.residence_label(ss.get("env_where")))
        st.caption(help_text)
    return stage_ui.chosen_residence("next")


def food_page():
    # --- start date: the typed "fully colonised on" date, else the Induction planning marker ---------------------
    if typed:
        default = typed
        source = (f"From your Monitor record: 'Fully colonised on' ({n_typed} sample(s) typed; the latest date is "
                  "used).")
    else:
        default = pipeline.induction_date(batch)
        source = (f"{pipeline.MARKER_LABEL}: the Colonisation forecast's 90% day + {pipeline.POST_90_DAYS} days "
                  "(project assumption). Type 'Fully colonised on' in Monitor to use your own date.")
        if default is None:
            source = "No forecast for this mushroom: choose the start date yourself."
    start = st.date_input("Start of induction", value=default, key="next_start")
    st.caption(source + " " + flow.FULLY_COLONISED_NOTE)

    residence = residence_section("Choose again if the batch moves for fruiting (for example from a box to a tent). "
                                  "Nothing chosen = it stays where it colonised.")

    br = pipeline.baseline_row(batch)
    if br is None:
        st.info("This mushroom has no row in the consensus guide, so there are no induction steps, fruiting ranges "
                "or dates.")
        return
    r, _ = br
    fr = bg.fruiting(r)
    acts = fr["induction_actions"]

    # --- what to do, in words ------------------------------------------------------------------------------------
    st.subheader("Induction steps")
    t = fr["fruiting_temp_C"]
    lines = [acts["overview"],
             f"**Temperature:** {acts['temperature']} (fruiting range {t['min']}–{t['max']} °C).",
             f"**Light:** {acts['light']}", f"**Fresh air:** {acts['fresh_air']}", f"**Humidity:** {acts['humidity']}"]
    st.markdown("\n".join(f"{i}. {line}" for i, line in enumerate(lines, start=1)))
    if fr["induction_evidence_status"] == "inferred_from_existing_columns":
        st.caption("These steps are inferred from other columns of the guide, not stated in it.")
    stage_ui.stage_cards(r, names=("Induction", "Fruiting", "Harvest"))

    # --- conditions check: fruiting ranges vs the latest reading of the next residence ----------------------------
    st.subheader("Conditions check")
    ranges = pipeline.next_stage_ranges(batch)
    reading = stage_ui.latest_reading("next", residence) if residence else {}
    stage_ui.conditions_check(ranges, reading)
    if reading:
        st.caption(f"Latest reading in {stage_ui.residence_label(residence)}: {reading['datetime'].replace('T', ' ')}. "
                   "Ranges: fruiting columns of the consensus guide.")
    else:
        st.caption(f"No reading yet for {stage_ui.residence_label(residence)}; log one on {monitor_title}.")

    # --- dates: consensus days, not a model ----------------------------------------------------------------------
    st.subheader("Dates")
    dates = pipeline.fruiting_dates(batch, start)
    if dates.value:
        for col, (label, day) in zip(st.columns(len(dates.value)), dates.value):
            col.metric(label, day.strftime("%d %b"), help="Consensus days from the guide, not a model")
    st.caption(dates.note)


def materials_page():
    # --- start date: the typed "fully colonised on" date, else ask (no forecast for materials yet) ----------------
    if typed:
        start = st.date_input("Start of post-treatment", value=typed, key="next_start")
        st.caption(f"From your Monitor record: 'Fully colonised on' ({n_typed} sample(s) typed; the latest date is "
                   "used).")
    else:
        start = st.date_input("Start of post-treatment", value=None, key="next_start")
        if start is None:
            st.info("No 'Fully colonised on' date is typed in Monitor yet. Choose the day the blocks are fully "
                    "colonised, or type it in Monitor.")

    residence_section("Where the blocks go after colonisation: an oven, a drying rack or room, or a press.")

    # --- method picker: one choice per ST6 protocol, with the values of our data -----------------------------------
    st.subheader("Method")
    methods = {m["protocol_id"]: m for m in pipeline.post_treatment_methods()}
    if not methods:
        st.warning("The post-treatment table is missing (run python -m dsr_mycodemo.post_treatment_data).")
        return
    ss.setdefault("pt_method", next(iter(methods)) if "OVEN-DRY" not in methods else "OVEN-DRY")
    method = st.radio("Post-treatment method", list(methods), key="pt_method",
                      format_func=lambda k: pipeline.post_treatment_label(methods[k]))
    st.markdown(pipeline.post_treatment_text(methods[method]))
    st.caption("Values from the post-treatment steps of the studies in our data (process.csv), summarised per "
               "method; nothing is filled in where a study gives no number.")

    # --- Material strength after colonisation, with the matched-pair note for the method ----------------------------
    out = flow.run().outcome
    st.subheader("Material strength")
    if out.is_preview:
        flow.preview(out.name, out.note)
    else:
        m1, m2 = st.columns(2)
        m1.metric("Stress at 10 % strain (after colonisation)", f"{out.value['stress_mpa']:.3f} MPa")
        m2.metric("Density (after colonisation)", f"{out.value['density']:.0f} kg/m³")
        st.caption(out.note)
    st.info(pipeline.post_treatment_note(method))


if materials:
    materials_page()
else:
    food_page()

if st.button(f"Next: {monitor_title.lower()}", type="primary", key="next"):
    st.switch_page("pages/8_Monitor_next_stage.py")
