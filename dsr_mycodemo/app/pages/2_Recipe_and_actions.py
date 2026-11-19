import streamlit as st

from dsr_mycodemo import pipeline
from dsr_mycodemo.app import flow, stage_ui
from dsr_mycodemo.cultivation import baseline_guide as bg
from dsr_mycodemo.cultivation import ingredients as ING

st.set_page_config(page_title="Recipe and actions",
                   page_icon="🧪", layout="wide")
flow.init()
ss = st.session_state
flow.need("environment", "Start a batch", "pages/1_Start_a_batch.py")

# our assumption: 1 L vessel = 0.2 kg dry substrate (as ENVIRONMENTS)
KG_DRY_PER_LITRE = 0.2
# 5% extra on everything, for handling
HANDLING = 1.05


def code(text, n):
    """First n letters of the words in text, upper case ('Shelf or vitrine' -> 'SHEL')."""
    letters = "".join(ch for ch in str(text or "") if ch.isalpha())
    return letters[:n].upper()


def suggest_label():
    """RESIDENCE-SPECIES-VESSEL-YYMMDD for Food, RESIDENCE-PRODUCT-VESSEL-YYMMDD for Materials."""
    if ss["goal"] == "Materials":
        what_code = code(ss["choice"], 4)
    else:
        latin = (flow.species_row() or {}).get(
            "species") or ss["custom_name"] or str(ss["choice"] or "")
        words = latin.split()
        what_code = (code(words[0], 1) + code(words[1], 2)
                     ) if len(words) > 1 else code(latin, 3)
    return "-".join([code(ss.get("env_where"), 4), what_code, code(ss.get("env_container"), 4),
                     ss["inoc_date"].strftime("%y%m%d")])


flow.header("Recipe and actions")
# vessels set on Start a batch: size x amount, summed (only the vessel chosen there counts; others may be stale)
vessel = ss.get("env_container")
ss["plan_size"] = None
vessel_litres = None
# moulds too
if vessel in stage_ui.vessels_for(flow.is_materials()) and vessel in ss.get("env_size", {}):
    vessel_litres = float(ss["env_size"][vessel])
    ss["plan_size"] = (int(ss["env_amount"].get(vessel, 1)),
                       vessel_litres * KG_DRY_PER_LITRE)

# keep these choices when the user visits another page
for k in [k for k in ss if str(k).startswith("rc_")]:
    ss[k] = ss[k]

# --- Step 3: the recipe, in a box (as Induction) --------------------------------------------------------
with st.container(border=True):
    st.subheader("Step 3. Build your recipe")
    pb = flow.get_batch()
    guide_species = pipeline.recipe_guide_species(pb)
    n_plan, kg_plan = pipeline._plan_size(pb)

    ss.setdefault("rc_method", "STER")
    method = st.radio("Sterilisation method", list(ING.METHODS),
                      key="rc_method", format_func=lambda k: ING.METHODS[k][0])
    STEP_NO = {key: (i + 1, title)
               for i, (key, title) in enumerate(ING.STEPS[method])}


    def step_heading(key):
        no, title = STEP_NO[key]
        st.markdown(f"#### {no}. {title}")


    # recipe table (Ingredient | choice | Include | % of dry weight | Total weight); step 1 of the actions below
    COLS = [1.6, 2.6, 0.8, 1.3, 1.3]
    for c, label in zip(st.columns(COLS), ["Ingredient", "Choice", "Include", "% of dry weight", "Total weight"]):
        c.markdown(f"**{label}**")

    OTHER = "__other__"
    main_ids = ING.main_options(pipeline.grower_species(pb))
    fallback_row, _ = bg.row(guide_species, bg.FALLBACK_SUBSTRATE)
    guide_text = bg.load_text().set_index("ref_id")
    default_main = ING.match_guide_words(
        guide_text.at[fallback_row["ref_id"], "substrate"])
    default_main = default_main if default_main in main_ids else ING.DEFAULT_MAIN
    main_key = f"rc_main_{guide_species}"
    if ss.get(main_key) not in main_ids + [OTHER]:
        ss[main_key] = default_main
    mc = st.columns(COLS, vertical_alignment="center")
    mc[0].write("Main bulk")
    main = mc[1].selectbox("Main bulk", main_ids + [OTHER], key=main_key, label_visibility="collapsed",
                           format_func=lambda k: "Other (type it)" if k == OTHER else ING.name(k))
    notes = []
    if main == OTHER:
        substrate = mc[1].text_input(
            "Other main material", key="rc_main_other").strip() or "other"
        substrate_code = pipeline.BASELINE_SUBSTRATE
        notes.append(
            "Not in the ingredient table: the guide's sawdust row is used and no mix C:N can be given.")
    else:
        substrate, substrate_code = ING.name(main), ING.guide_substrate_code(main)
        if ING.load().at[main, "wood_type"] == "soft":
            notes.append(ING.SOFTWOOD_NOTE +
                         " A Quick energy supplement can help.")
    ss["substrate"] = substrate
    main_pct_cell, main_weight_cell = mc[3].empty(), mc[4].empty()

    # supplement rows by function: one dropdown + tick box each; guide amounts and ticks for this species and main
    guide_row, _ = bg.row(guide_species, substrate_code)
    ref = guide_row["ref_id"]
    from_guide, guide_left = ING.guide_supplements(
        guide_text.at[ref, "substrate_supplementation"])
    in_rows = {i for ids in ING.supplement_rows().values() for i in ids}
    rows = ING.supplement_rows(
        [i for i in from_guide if i not in in_rows and i != main])
    chosen, weight_cells = [], {}
    for rk, ids in rows.items():
        title = ING.ROWS[rk][0]
        c = st.columns(COLS, vertical_alignment="center")
        c[0].write(title)
        pick_key = f"rc_pick_{ref}_{rk}"
        if ss.get(pick_key) not in ids:
            ss[pick_key] = next((i for i in ids if i in from_guide), ids[0])
        i = c[1].selectbox(title, ids, key=pick_key,
                           format_func=ING.name, label_visibility="collapsed")
        tick_key, pct_key = f"rc_tick_{ref}_{method}_{i}", f"rc_pct_{ref}_{i}"
        ss.setdefault(tick_key, ING.default_ticked(
            i, method, from_guide.get(i, {}).get("ticked", False)))
        ss.setdefault(pct_key, float(from_guide.get(
            i, {}).get("pct", ING.DEFAULT_PCT.get(i, 5.0))))
        if c[2].checkbox(f"Include {title}", key=tick_key, label_visibility="collapsed"):
            pct = c[3].number_input(f"% of dry weight ({title})", 0.0, 60.0, step=0.5, key=pct_key,
                                    label_visibility="collapsed")
            chosen.append(
                {"ingredient": i, "name": ING.name(i), "pct": float(pct)})
            weight_cells[i] = c[4].empty()
        else:
            c[3].caption(f"{ss[pct_key]:g} %")

    # weights, recalculated on every change (5% extra for handling); g, or kg when the sum is 1000 g or more
    supp_pct = sum(c["pct"] for c in chosen)
    mix = None
    if supp_pct < 100:
        mix = {"main_name": substrate, "supplements": [
            {"name": c["name"], "pct": c["pct"]} for c in chosen]}
    moisture = float(guide_row["substrate_moisture_pct"])
    amt = ING.amounts(kg_plan, moisture, n_plan, method,
                      pipeline.SPAWN_PCT, HANDLING)
    unit = ING.unit_for(amt["sum"])


    def w(grams):
        return ING.fmt_weight(grams, unit)


    main_pct_cell.caption(f"{max(100 - supp_pct, 0):g} %")
    main_weight_cell.write(
        w(amt["dry_total"] * (1 - supp_pct / 100)) if mix else "–")
    for c in chosen:
        weight_cells[c["ingredient"]].write(
            w(amt["dry_total"] * c["pct"] / 100) if mix else "–")
    if amt["water_total"] is not None:
        c = st.columns(COLS, vertical_alignment="center")
        c[0].write("Water")
        c[1].caption(f"to {moisture:g} % moisture")
        c[4].write(w(amt["water_total"]))
    c = st.columns(COLS, vertical_alignment="center")
    c[0].markdown("**Sum**")
    c[1].caption("dry ingredients + water" if amt["water_total"]
                 is not None else "dry ingredients")
    c[4].markdown(f"**{w(amt['sum'])}**")
    st.caption("5% extra on everything is included here for handling.")
    if mix is None:
        st.error(f"The ticked supplements add up to {supp_pct:g} % of the dry mix; lower them so the main bulk "
                 "keeps a share. The guide's own mix is used until then.")
    if guide_left:
        st.caption("Also from the guide: " + "; ".join(guide_left) + ".")

    ticked_groups = {ING.load().at[c["ingredient"], g] for c in chosen if c["ingredient"] in ING.load().index
                     for g in ("group_1", "group_2")}
    if "QSUR" in ticked_groups:
        notes.append(ING.QUICK_ENERGY_NOTE)
    if method != "STER" and any(ING.load().at[c["ingredient"], "group_1"] in ING.RISKY_UNSTERILISED
                                for c in chosen if c["ingredient"] in ING.load().index):
        notes.append(ING.UNSTERILISED_NOTE)
    if method == "COLD":
        notes.append(ING.COLD_NOTE)
    if notes:
        st.info("\n\n".join(notes))
    parts = {**({main: 100 - supp_pct} if main != OTHER else {}),
             **{c["ingredient"]: c["pct"] for c in chosen}}
    # without the bulk the ratio would mislead
    cn = ING.mix_cn(parts) if main != OTHER else None
    st.metric("Mix C:N (estimate)", "n/a" if cn is None else f"{cn:.0f}:1",
              help="Sum of weight × C% over sum of weight × N% of the dry ingredients; spawn not counted.")
    if ING.uses_category_values(parts):
        st.caption("(some values are typical for their category)")

# --- Step 4: inoculation, in a box ---------------------------------------------------------------------
with st.container(border=True):
    st.subheader("Step 4. Inoculation")
    d1, d2 = st.columns(2)
    ss["inoc_date"] = d1.date_input("Inoculation date", ss["inoc_date"])
    auto = suggest_label()
    # follow the suggestion until the user edits it
    if ss.get("batch_label") in (None, "", ss.get("batch_label_auto")):
        ss["batch_label"] = auto
    ss["batch_label_auto"] = auto
    batch_label = d2.text_input("Batch label", key="batch_label",
                                help="Suggested automatically; you can change it.")
    step_heading("recipe")
    if method == "STER":
        st.markdown(f"Weight of mix for each vessel: **{w(amt['per_vessel'])}** (dry + water, before spawn; "
                    f"{n_plan} vessel{'s' if n_plan > 1 else ''}).")

    # step 2: sterilise or pasteurise
    autoclave_min = jar_size = None
    step_heading("treat")
    if method == "STER":
        has_vessel = vessel_litres is not None
        if has_vessel:
            jar_size = ING.autoclave_size_key(
                vessel_litres, amt["per_vessel"] / 1000)
        autoclave_min, line = ING.autoclave_line(vessel if has_vessel else None, vessel_litres, n_plan,
                                                 amt["per_vessel"] / 1000)
        (st.info if not has_vessel else st.warning if autoclave_min is None else st.markdown)(line)
    else:
        st.markdown(ING.METHODS[method][2])

    # step 3: spawn (not in the sum above)
    step_heading("spawn")
    spawn_line = (f"Spawn: **{w(amt['spawn_per_vessel'])}** per vessel, {w(amt['spawn_total'])} in all "
                  f"({pipeline.SPAWN_PCT:g} % of the whole mix).")
    if method == "STER":
        st.markdown(ING.COOL_SPAWN_CLOSE + "\n\n" + spawn_line)
    else:
        st.markdown((ING.COOL_MIX_FILL if method == "STEAM" else
                     "No cooling needed: mix all the spawn into the whole batch, then fill the vessels.")
                    + "\n\n" + spawn_line +
                    f"\n\nWeight of mix for each vessel: **{w(amt['per_vessel'])}** "
                    f"(damp mix + spawn; {n_plan} vessel{'s' if n_plan > 1 else ''}).")

    ss["recipe"] = {"substrate": substrate_code, "spawn_pct": pipeline.SPAWN_PCT, "method": method,
                    "protocol_id": ING.METHODS[method][1], "jar_size": jar_size, "autoclave_min": autoclave_min,
                    "main": None if main == OTHER else main, "supplements": chosen, "mix": mix, "mix_cn": cn}
    result = flow.run()
    batch = flow.get_batch()
    what = flow.choice_label()
    rv = result.recipe.value
    n = rv["n"]
    if flow.is_materials():
        st.caption(result.recipe.note)

    # --- days to the next step: Food = the Colonisation time estimate as dates; Materials = greyed previews ------
    st.subheader("Days to the next step")
    if flow.is_materials():
        stage_ui.materials_timing_previews()
    else:
        stage_ui.colonisation_days(result, compact=True)

# --- induction / post-treatment steps, shown on request (show_next_steps) --------------------------------
ss.setdefault("show_next_steps", False)
next_title = stage_ui.next_titles(flow.is_materials())
if st.button(("Hide " if ss["show_next_steps"] else "Show ") + f"{next_title.lower()} steps", key="show_next_steps_btn"):
    ss["show_next_steps"] = not ss["show_next_steps"]
    st.rerun()
if ss["show_next_steps"]:
    with st.container(border=True):
        st.subheader(next_title)
        if flow.is_materials():
            stage_ui.post_treatment_section(ss.get("batch"), result)
        else:
            stage_ui.induction_section(flow.sample_batch(), ss.get("batch"))

# --- warnings -----------------------------------------------------------------------------------
if result.warnings.is_preview:
    flow.preview(result.warnings.name, result.warnings.note)
for w in result.warnings.value:
    st.warning(w)

# --- harvest record or strength -------------------------------------------------------------
out = result.outcome
if ss["goal"] != "Food":
    st.subheader(out.name + " estimate")
    if out.is_preview:
        flow.preview(out.name, out.note)
    else:
        m1, m2 = st.columns(2)
        m1.metric("Stress at 10 % strain",
                  f"{out.value['stress_mpa']:.3f} MPa")
        m2.metric("Density", f"{out.value['density']:.0f} kg/m³")
        st.markdown(f"**{out.value['species']}** on **{out.value['substrate_group']}**: {out.value['label']}. Based "
                    f"on {out.value['n_pair']} rows for this species on {out.value['substrate_group']} "
                    f"({out.value['n_rows']} for this species, out of {out.value['n_total']}).")
        st.caption(out.note)

# --- hand over to Monitor ----------------------------------------------------------------
if st.button("Save this plan and open Monitor", type="primary"):
    row = flow.species_row()
    label = batch_label or f"{what} {ss['inoc_date'].isoformat()}"
    # a new batch: its stage starts again on Monitor
    if (ss.get("batch") or {}).get("batch_label") != label:
        for k in ("batch_stage", "next_start"):
            ss.pop(k, None)
    ss["batch"] = {"batch_label": label,
                   "species": row["species"] if row else ss["material_species"] if flow.is_materials() else what,
                   "inoc_date": ss["inoc_date"], "n_containers": n, "temp_c": ss["temp_c"],
                   "substrate": substrate, "spawn_pct": float(pipeline.SPAWN_PCT)}
    st.switch_page("pages/3_Monitor.py")
