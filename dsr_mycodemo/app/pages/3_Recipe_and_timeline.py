"""Recipe and timeline: the recipe as steps in the order of the sterilisation method, then colonisation and the
stage timeline in one figure, stage bubbles, and the harvest note or strength."""

import html
import math

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from dsr_mycodemo import pipeline
from dsr_mycodemo.app import flow
from dsr_mycodemo.cultivation import baseline_guide as bg
from dsr_mycodemo.cultivation import ingredients as ING

st.set_page_config(page_title="Recipe and timeline", page_icon="🧪", layout="wide")
flow.init()
ss = st.session_state
flow.need("environment", "Environment", "pages/2_Environment.py")

VESSELS = ["Glass Jar", "Tupperware", "Grow bag", "Bucket"]   # all vessel names of the Environment page
KG_DRY_PER_LITRE = 0.2                               # our assumption: 1 L vessel = 0.2 kg dry substrate (as ENVIRONMENTS)
HANDLING = 1.05                                      # 5% extra on everything, for handling
EVENT_COLOR, STAGE_COLOR = "#8A5A3B", "#5E6B3A"


def code(text, n):
    """First n letters of the words in text, upper case ('Shelf or vitrine' -> 'SHEL')."""
    letters = "".join(ch for ch in str(text or "") if ch.isalpha())
    return letters[:n].upper()


def suggest_label():
    """RESIDENCE-SPECIES-VESSEL-YYMMDD for Food, RESIDENCE-PRODUCT-VESSEL-YYMMDD for Materials."""
    if ss["goal"] == "Materials":
        what_code = code(ss["choice"], 4)
    else:
        latin = (flow.species_row() or {}).get("species") or ss["custom_name"] or str(ss["choice"] or "")
        words = latin.split()
        what_code = (code(words[0], 1) + code(words[1], 2)) if len(words) > 1 else code(latin, 3)
    return "-".join([code(ss.get("env_where"), 4), what_code, code(ss.get("env_container"), 4),
                     ss["inoc_date"].strftime("%y%m%d")])


flow.step_header(3, 6, "Recipe and timeline")
d1, d2 = st.columns(2)
ss["inoc_date"] = d1.date_input("Planned inoculation date", ss["inoc_date"])
auto = suggest_label()
if ss.get("batch_label") in (None, "", ss.get("batch_label_auto")):   # follow the suggestion until the user edits it
    ss["batch_label"] = auto
ss["batch_label_auto"] = auto
batch_label = d2.text_input("Batch label", key="batch_label", help="Suggested automatically; you can change it.")

# vessels set on Environment: size x amount, summed (only the vessel chosen there counts; others may be stale)
vessel = ss.get("env_container")
ss["plan_size"] = None
vessel_litres = None
if vessel in VESSELS and vessel in ss.get("env_size", {}):
    vessel_litres = float(ss["env_size"][vessel])
    ss["plan_size"] = (int(ss["env_amount"].get(vessel, 1)), vessel_litres * KG_DRY_PER_LITRE)

# --- recipe as steps, in the order the chosen method needs -----------------------------------------
for k in [k for k in ss if str(k).startswith("rc_")]:   # keep these choices when the user visits another page
    ss[k] = ss[k]
st.subheader("Recipe")
pb = flow.get_batch()
guide_species = pipeline.recipe_guide_species(pb)
n_plan, kg_plan = pipeline._plan_size(pb)

ss.setdefault("rc_method", "STER")
method = st.radio("Sterilisation method", list(ING.METHODS), key="rc_method", format_func=lambda k: ING.METHODS[k][0])
STEP_NO = {key: (i + 1, title) for i, (key, title) in enumerate(ING.STEPS[method])}


def step_heading(key):
    no, title = STEP_NO[key]
    st.markdown(f"#### {no}. {title}")


# step 1: recipe table (Ingredient | choice | Include | % of dry weight | Total weight)
step_heading("recipe")
COLS = [1.6, 2.6, 0.8, 1.3, 1.3]
for c, label in zip(st.columns(COLS), ["Ingredient", "Choice", "Include", "% of dry weight", "Total weight"]):
    c.markdown(f"**{label}**")

OTHER = "__other__"
main_ids = ING.main_options(pipeline.grower_species(pb))
fallback_row, _ = bg.row(guide_species, bg.FALLBACK_SUBSTRATE)
guide_text = bg.load_text().set_index("ref_id")
default_main = ING.match_guide_words(guide_text.at[fallback_row["ref_id"], "substrate"])
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
    substrate = mc[1].text_input("Other main material", key="rc_main_other").strip() or "other"
    substrate_code = pipeline.BASELINE_SUBSTRATE
    notes.append("Not in the ingredient table: the guide's sawdust row is used and no mix C:N can be given.")
else:
    substrate, substrate_code = ING.name(main), ING.guide_substrate_code(main)
    if ING.load().at[main, "wood_type"] == "soft":
        notes.append(ING.SOFTWOOD_NOTE + " A Quick energy supplement can help.")
ss["substrate"] = substrate
main_pct_cell, main_weight_cell = mc[3].empty(), mc[4].empty()

# supplement rows by function: one dropdown + tick box each; guide amounts and ticks for this species and main
guide_row, _ = bg.row(guide_species, substrate_code)
ref = guide_row["ref_id"]
from_guide, guide_left = ING.guide_supplements(guide_text.at[ref, "substrate_supplementation"])
in_rows = {i for ids in ING.supplement_rows().values() for i in ids}
rows = ING.supplement_rows([i for i in from_guide if i not in in_rows and i != main])
chosen, weight_cells = [], {}
for rk, ids in rows.items():
    title = ING.ROWS[rk][0]
    c = st.columns(COLS, vertical_alignment="center")
    c[0].write(title)
    pick_key = f"rc_pick_{ref}_{rk}"
    if ss.get(pick_key) not in ids:
        ss[pick_key] = next((i for i in ids if i in from_guide), ids[0])
    i = c[1].selectbox(title, ids, key=pick_key, format_func=ING.name, label_visibility="collapsed")
    tick_key, pct_key = f"rc_tick_{ref}_{method}_{i}", f"rc_pct_{ref}_{i}"
    ss.setdefault(tick_key, ING.default_ticked(i, method, from_guide.get(i, {}).get("ticked", False)))
    ss.setdefault(pct_key, float(from_guide.get(i, {}).get("pct", ING.DEFAULT_PCT.get(i, 5.0))))
    if c[2].checkbox(f"Include {title}", key=tick_key, label_visibility="collapsed"):
        pct = c[3].number_input(f"% of dry weight ({title})", 0.0, 60.0, step=0.5, key=pct_key,
                                label_visibility="collapsed")
        chosen.append({"ingredient": i, "name": ING.name(i), "pct": float(pct)})
        weight_cells[i] = c[4].empty()
    else:
        c[3].caption(f"{ss[pct_key]:g} %")

# weights, recalculated on every change (5% extra for handling); g, or kg when the sum is 1000 g or more
supp_pct = sum(c["pct"] for c in chosen)
mix = None
if supp_pct < 100:
    mix = {"main_name": substrate, "supplements": [{"name": c["name"], "pct": c["pct"]} for c in chosen]}
moisture = float(guide_row["substrate_moisture_pct"])
amt = ING.amounts(kg_plan, moisture, n_plan, method, pipeline.SPAWN_PCT, HANDLING)
unit = ING.unit_for(amt["sum"])


def w(grams):
    return ING.fmt_weight(grams, unit)


main_pct_cell.caption(f"{max(100 - supp_pct, 0):g} %")
main_weight_cell.write(w(amt["dry_total"] * (1 - supp_pct / 100)) if mix else "–")
for c in chosen:
    weight_cells[c["ingredient"]].write(w(amt["dry_total"] * c["pct"] / 100) if mix else "–")
if amt["water_total"] is not None:
    c = st.columns(COLS, vertical_alignment="center")
    c[0].write("Water")
    c[1].caption(f"to {moisture:g} % moisture")
    c[4].write(w(amt["water_total"]))
c = st.columns(COLS, vertical_alignment="center")
c[0].markdown("**Sum**")
c[1].caption("dry ingredients + water" if amt["water_total"] is not None else "dry ingredients")
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
if main != OTHER and ING.form_caption(main):
    st.caption(ING.form_caption(main))

parts = {**({main: 100 - supp_pct} if main != OTHER else {}), **{c["ingredient"]: c["pct"] for c in chosen}}
cn = ING.mix_cn(parts) if main != OTHER else None      # without the bulk the ratio would mislead
st.metric("Mix C:N (estimate)", "n/a" if cn is None else f"{cn:.0f}:1",
          help="Sum of weight × C% over sum of weight × N% of the dry ingredients; spawn not counted.")
if ING.uses_category_values(parts):
    st.caption("(some values are typical for their category)")
if method == "STER":
    st.markdown(f"Weight of mix for each vessel: **{w(amt['per_vessel'])}** (dry + water, before spawn; "
                f"{n_plan} vessel{'s' if n_plan > 1 else ''}).")

# step 2: sterilise or pasteurise
autoclave_min = jar_size = None
step_heading("treat")
if method == "STER":
    has_vessel = vessel_litres is not None
    if has_vessel:
        jar_size = ING.autoclave_size_key(vessel_litres, amt["per_vessel"] / 1000)
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
                + "\n\n" + spawn_line + f"\n\nWeight of mix for each vessel: **{w(amt['per_vessel'])}** "
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

# --- colonisation (top) and stage timeline (bottom), one figure on one days axis ---------------------
est, fc, dates = result.colonisation_estimate, result.colonisation_forecast, result.dates


def logistic(x, t90, c0=0.02, c90=0.90, start=0.0):
    """Logistic through (start, c0) and (t90, c90); x in days."""
    def logit(c):
        return math.log(c / (1 - c))
    k = (logit(c90) - logit(c0)) / (t90 - start)
    mid = t90 - logit(c90) / k
    return [100 / (1 + math.exp(-k * (xi - mid))) for xi in x]


def colonisation_setup():
    """(t90, photos) for the curve, or None when there is no estimate."""
    if est.is_preview or est.value is None:
        return None
    photos = sorted((p for p in batch.photos if p.day >= 0 and not p.quality), key=lambda p: p.day)
    t90 = float(est.value["typical"])
    if photos and fc.value is not None and fc.value.get("method") in ("curve fit", "consensus update"):
        t90 = float(fc.value["day90"])                      # Colonisation forecast (3 or more photos)
    return (t90, photos) if t90 > 0 else None


def colonisation_traces(t90, photos, x_end):
    """Dotted = estimate or forecast (S-curve assumed), solid = measured photos; drawn to x_end."""
    out = []
    if not photos:
        xs = [x_end * i / 80 for i in range(81)]
        out.append(go.Scatter(x=xs, y=logistic(xs, t90), mode="lines", line=dict(dash="dot", color=STAGE_COLOR),
                              name="Estimate"))
        return out
    pd_, pc = [p.day for p in photos], [100 * p.coverage for p in photos]
    out.append(go.Scatter(x=[0] + pd_, y=[0] + pc, mode="lines", line=dict(color=STAGE_COLOR), name="Measured",
                          hoverinfo="skip"))
    out.append(go.Scatter(x=pd_, y=pc, mode="markers", marker=dict(size=9, color=STAGE_COLOR), name="Photos",
                          hovertemplate="day %{x}: %{y:.0f}%<extra></extra>"))
    last_d, last_c = pd_[-1], min(max(pc[-1], 2.0), 98.0)
    if last_c < 90 and t90 > last_d:
        xs = [last_d + (x_end - last_d) * i / 60 for i in range(61)]
        out.append(go.Scatter(x=xs, y=logistic(xs, t90, c0=last_c / 100, start=last_d), mode="lines",
                              line=dict(dash="dot", color=STAGE_COLOR), name="Forecast"))
    return out


def colonisation_caption(t90, photos):
    src = "the Colonisation forecast" if t90 != float(est.value["typical"]) else "the Colonisation time estimate"
    return (f"Top: % colonised. Dotted: {src} (90% on day {t90:.0f}); the S-curve shape is our assumption. "
            + ("Solid: measured from your photos in Monitor. " if photos else
               "Photos added in Monitor are drawn as points with a solid line. ")
            + "If the temperature changes, the estimate is re-run and the dotted part moves.")


def timeline_traces(ind_day, har_day):
    out = []
    for name, x0, x1 in (("Colonising", 0, ind_day), ("Fruiting", ind_day, har_day)):
        out.append(go.Bar(y=["Timeline"], x=[x1 - x0], base=[x0], orientation="h", name=name, width=0.45,
                          marker_color=STAGE_COLOR, opacity=0.45 if name == "Colonising" else 0.7,
                          text=name, textposition="inside", insidetextanchor="middle",
                          hovertemplate=f"{name}: day {x0:g}–{x1:g}<extra></extra>"))
    for name, day in (("Inoculation", 0), ("Induction", ind_day), ("Harvest", har_day)):
        out.append(go.Scatter(x=[day], y=["Timeline"], mode="markers+text", name=name,
                              marker=dict(symbol="line-ns", size=36, line=dict(width=3, color=EVENT_COLOR)),
                              text=[f"{name}<br>day {int(day)}"], textposition="top center"))
    return out


def draw(col_setup, tl_days):
    """One figure: colonisation on top (if any), stage timeline below (if any), shared days axis from 0 to the
    harvest day or the end of the forecast, whichever is later."""
    parts = [p for p in ("col" if col_setup else None, "tl" if tl_days else None) if p]
    if not parts:
        return
    natural_end = 0.0
    if col_setup:
        t90, photos = col_setup
        natural_end = max(t90 * 1.25, max((p.day for p in photos), default=0))
    x_end = max(natural_end, tl_days[1] if tl_days else 0)
    fig = make_subplots(rows=len(parts), cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        row_heights=[0.65, 0.35] if len(parts) == 2 else None)
    if col_setup:
        for tr in colonisation_traces(t90, photos, x_end):
            fig.add_trace(tr, row=1, col=1)
        fig.add_hline(y=90, line_dash="dot", line_color="#9aa0a6", annotation_text="90%", row=1, col=1)
        fig.add_vline(x=t90, line_dash="dot", line_color="#9aa0a6", annotation_text=f"day {t90:.0f}", row=1, col=1)
        fig.update_yaxes(title_text="% colonised", range=[0, 100], row=1, col=1)
    if tl_days:
        for tr in timeline_traces(*tl_days):
            fig.add_trace(tr, row=len(parts), col=1)
        fig.update_yaxes(showticklabels=False, row=len(parts), col=1)
    fig.update_xaxes(range=[0, x_end * 1.03])
    fig.update_xaxes(title_text="Days since inoculation", row=len(parts), col=1)
    fig.update_layout(height=230 + 250 * bool(col_setup), margin=dict(l=10, r=10, t=30, b=40), showlegend=False,
                      barmode="overlay")
    st.plotly_chart(fig, use_container_width=True)
    caption = colonisation_caption(t90, photos) if col_setup else ""
    if tl_days:
        caption += (" Bottom: stages (bars) and events (ticks) on the guide's typical days. Induction falls on the "
                    "typical day colonisation ends; Harvest is the typical first-harvest day counted from the start "
                    "of induction.")
    st.caption(caption.strip())


col_setup = colonisation_setup()
base = pipeline.baseline_row(batch)
if base is None and col_setup:
    st.subheader("Colonisation")
    draw(col_setup, None)
if base is not None:
    r, row_note = base
    temp = ss["temp_c"]
    species = r["species"]
    st.subheader("Colonisation and stage timeline")
    t = bg.load_text()
    t = t[t["ref_id"] == r["ref_id"]].iloc[0]
    col, fr = bg.colonisation(r), bg.fruiting(r)
    inc = col["incubation_temp_C"]
    state = bg.temp_check(temp, inc["min"], inc["max"])
    (st.success if state == "inside" else st.warning)(
        f"{temp:g} °C is {state} the colonisation range ({inc['min']}–{inc['max']} °C)."
        + ("" if state == "inside" else " The days below assume the guide's own conditions."))

    tl = bg.stages(r).set_index("stage")
    ind_row, har_row = tl.loc["Start induction"], tl.loc["First harvest"]
    ind_day, har_day, col_days = ind_row["typical_day"], har_row["typical_day"], col["colonisation_days"]
    draw(col_setup, (ind_day, har_day))

    # --- stage bubbles, one row: name · days, then temperature, humidity, CO2, light -------------------
    NIG = "not in guide"

    def val(x, unit="", before=""):
        return NIG if str(x) in ("", "nan", "None") else f"{before}{x:g}{unit}"

    def rng(lo, hi, unit):
        return NIG if str(lo) == "nan" or str(hi) == "nan" else (f"{lo:g}–{hi:g}{unit}" if lo != hi else f"{lo:g}{unit}")

    def span(label):
        s_ = tl.loc[label]
        return f"day {s_['start_day']}–{s_['end_day']} (typical {s_['typical_day']})"

    inc_c = (rng(r["incubation_temp_min_C"], r["incubation_temp_max_C"], " °C"),
             val(r["incubation_RH_pct"], " %", ">"), "high CO2 fine (closed)", "not required")
    fr_c = (rng(r["fruiting_temp_min_C"], r["fruiting_temp_max_C"], " °C"),
            rng(r["fruiting_RH_min_pct"], r["fruiting_RH_max_pct"], " %"),
            val(r["fruiting_CO2_max_ppm"], " ppm", "< "), "500-1000 lux")
    bubbles = [(EVENT_COLOR, "Inoculation", "day 0", inc_c),
               (STAGE_COLOR, "Colonising", f"day {col_days['min']}–{col_days['max']} (typical {col_days['typical']})",
                inc_c),
               (EVENT_COLOR, "Induction", span("Start induction"), fr_c),
               (STAGE_COLOR, "Fruiting", (f"day {ind_row['start_day']}–{har_row['end_day']} "
                                          f"(typical {ind_day:g}–{har_day:g})"), fr_c),
               (EVENT_COLOR, "Harvest", span("First harvest"), fr_c)]
    for box, (color, name, when, (tmp, rh, co2, lt)) in zip(st.columns(5), bubbles):
        body = (f"<b>{html.escape(name)}</b> · {html.escape(when)}<br>🌡️ {html.escape(tmp)}<br>💧 {html.escape(rh)}"
                f"<br>🌬️ {html.escape(co2)}<br>💡 {html.escape(lt)}")
        box.markdown(f"<div style='border:2px solid {color}; border-left:8px solid {color}; border-radius:8px; "
                     f"padding:0.6rem 0.8rem; margin:0.4rem 0; height:100%;'>{body}</div>", unsafe_allow_html=True)
    if species == "Lentinula edodes":
        st.info(f"Unresolved: {t['requirements_unresolved']}")

    st.caption(f"Source: {col['source']} · evidence: {r['evidence_type']} · confidence: {col['confidence']}. "
               f"Row used: {row_note}. Consensus values, not a prediction. CO2 for colonisation and light are "
               "general consensus.")
elif flow.is_materials():
    st.subheader("Colonisation and timeline")
    for title in ("Colonisation time estimate (days)", "Colonisation forecast (90% day and dates)",
                  "Stage timeline and " + pipeline.MARKER_LABEL):
        flow.materials_preview(title)
else:
    st.subheader("Stage 1: Colonisation")
    if est.is_preview:
        flow.preview("Colonisation time estimate", est.note)
    else:
        lo, hi = est.value["days"]
        ev1 = {n: (a, b) for n, a, b in dates.value}
        full = ev1[pipeline.ENDPOINT_LABEL]

        def span1(a, b):
            return f"{a.strftime('%d %b')} – {b.strftime('%d %b')}"

        c1, c2, c3 = st.columns(3)
        c1.metric(pipeline.ENDPOINT_LABEL, span1(*full), help="Project assumption")
        mk = ev1.get(pipeline.MARKER_LABEL)
        if mk:
            c2.metric(pipeline.MARKER_LABEL, span1(*mk), help="Project assumption: the 90% day + 2 days")
        c3.metric("Duration to 90%", f"{lo:.0f}–{hi:.0f} days", help=f"Typical {est.value['typical']:.0f} days")
        st.progress(0.0, text=f"Day 0 → day {hi:.0f}")
        st.caption(flow.ENDPOINT_ASSUMPTION_NOTE)
        flow.show_source(est)
        if fc.value is not None and fc.value["method"] != "estimate":
            st.caption(f"Your photos have changed this: {fc.note}")
        else:
            st.caption("Your photos in Monitor will update it into the Colonisation forecast.")

# --- warnings -----------------------------------------------------------------------------------
if result.warnings.is_preview:
    flow.preview(result.warnings.name, result.warnings.note)
for w in result.warnings.value:
    st.warning(w)

# --- harvest record or strength -------------------------------------------------------------
out = result.outcome
if ss["goal"] == "Food":
    st.info("Yield: record your harvest in Monitor.")
else:
    st.subheader(out.name + " estimate")
    if out.is_preview:
        flow.preview(out.name, out.note)
    else:
        m1, m2 = st.columns(2)
        m1.metric("Stress at 10 % strain", f"{out.value['stress_mpa']:.3f} MPa")
        m2.metric("Density", f"{out.value['density']:.0f} kg/m³")
        st.markdown(f"**{out.value['species']}**: {out.value['label']}. Based on {out.value['n_rows']} rows for this "
                    f"species, out of {out.value['n_total']}.")
        st.caption(out.note)

if result.harvest_readiness is not None:
    flow.preview("Harvest readiness", result.harvest_readiness.note)

# --- hand over to Monitor ----------------------------------------------------------------
if st.button("Save this plan and open Monitor", type="primary"):
    row = flow.species_row()
    ss["batch"] = {"batch_label": batch_label or f"{what} {ss['inoc_date'].isoformat()}",
                   "species": row["species"] if row else ss["material_species"] if flow.is_materials() else what,
                   "inoc_date": ss["inoc_date"], "n_containers": n, "temp_c": ss["temp_c"],
                   "substrate": substrate, "spawn_pct": float(pipeline.SPAWN_PCT)}
    st.switch_page("pages/4_Monitor.py")
