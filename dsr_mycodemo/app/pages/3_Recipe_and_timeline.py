"""Recipe and timeline: shows what the pipeline returns (recipe, colonisation timeline, harvest note or strength)."""

import html
import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dsr_mycodemo import pipeline
from dsr_mycodemo.app import flow
from dsr_mycodemo.cultivation import baseline_guide as bg
from dsr_mycodemo.cultivation import ingredients as ING
from dsr_mycodemo.cultivation import recipe as recipe_maths

st.set_page_config(page_title="Recipe and timeline", page_icon="🧪", layout="wide")
flow.init()
ss = st.session_state
flow.need("environment", "Environment", "pages/2_Environment.py")

VESSELS = ["Tupperware", "Grow bag", "Bucket"]       # the vessel names of the Environment page
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

# --- recipe choices: treatment method, main material, supplements ------------------------------
for k in [k for k in ss if str(k).startswith("rc_")]:   # keep these choices when the user visits another page
    ss[k] = ss[k]
st.subheader("Recipe")
pb = flow.get_batch()
guide_species = pipeline.recipe_guide_species(pb)
n_plan, kg_plan = pipeline._plan_size(pb)

# 1. treatment method
ss.setdefault("rc_method", "STER")
method = st.radio("Treatment method", list(ING.METHODS), key="rc_method", format_func=lambda k: ING.METHODS[k][0])
autoclave_min = jar_size = None
if method == "STER":
    sizes = list(ING.AUTOCLAVE_SIZES)
    auto_jar = ING.autoclave_size_key(vessel_litres, kg_plan + recipe_maths.water_to_add(kg_plan, 65))
    if ss.get("rc_jar") in (None, ss.get("rc_jar_auto")):           # follow page 2 until the user picks a size
        ss["rc_jar"] = auto_jar
    ss["rc_jar_auto"] = auto_jar
    jar_size = st.selectbox("Size of each jar or bag", sizes, key="rc_jar",
                            format_func=lambda k: ING.AUTOCLAVE_SIZES[k][0])
    autoclave_min, how = ING.autoclave_time(jar_size)
    (st.warning if autoclave_min is None else st.caption)(how)
else:
    st.caption(ING.METHODS[method][2])

# 2. main material (bulk)
OTHER = "__other__"
main_ids = ING.main_options(pipeline.grower_species(pb))
fallback_row, _ = bg.row(guide_species, bg.FALLBACK_SUBSTRATE)
guide_text = bg.load_text().set_index("ref_id")
default_main = ING.match_guide_words(guide_text.at[fallback_row["ref_id"], "substrate"])
default_main = default_main if default_main in main_ids else ING.DEFAULT_MAIN
main_key = f"rc_main_{guide_species}"
if ss.get(main_key) not in main_ids + [OTHER]:
    ss[main_key] = default_main
main = st.selectbox("Main material", main_ids + [OTHER], key=main_key,
                    format_func=lambda k: "Other (type it)" if k == OTHER else ING.name(k))
if main == OTHER:
    substrate = st.text_input("Other main material", key="rc_main_other").strip() or "other"
    substrate_code = pipeline.BASELINE_SUBSTRATE
    st.caption("Not in the ingredient table: the guide's sawdust row is used and no mix C:N can be given.")
else:
    substrate, substrate_code = ING.name(main), ING.guide_substrate_code(main)
    if ING.form_caption(main):
        st.caption(ING.form_caption(main))
    if ING.load().at[main, "wood_type"] == "soft":
        st.caption(ING.SOFTWOOD_NOTE + " A Quick energy supplement (below) can help.")
ss["substrate"] = substrate

# 3. supplements by function: guide amounts and ticks for this species on this main material
guide_row, _ = bg.row(guide_species, substrate_code)
ref = guide_row["ref_id"]
from_guide, _ = ING.guide_supplements(guide_text.at[ref, "substrate_supplementation"])
groups = ING.supplement_groups()
in_groups = {i for ids in groups.values() for i in ids}
extra = [i for i in from_guide if i not in in_groups and i != main]
if extra:
    groups = {**groups, "GUIDE": extra}
chosen = []
for g, ids in groups.items():
    title, purpose = ING.GROUPS.get(g, ("Also in the guide's mix", "Other ingredients the guide row names."))
    st.markdown(f"**{title}**")
    st.caption(purpose + (" Raises mould risk unless sterilised."
                          if g in ING.RISKY_UNSTERILISED and method != "STER" else ""))
    for i in ids:
        g2 = ING.load().at[i, "group_2"] if i in ING.load().index else ""
        tick_key, pct_key = f"rc_tick_{ref}_{method}_{i}", f"rc_pct_{ref}_{i}"
        ss.setdefault(tick_key, ING.default_ticked(i, method, from_guide.get(i, {}).get("ticked", False)))
        ss.setdefault(pct_key, float(from_guide.get(i, {}).get("pct", ING.DEFAULT_PCT.get(i, 5.0))))
        c1, c2 = st.columns([3, 1])
        label = ING.name(i) + (f" · also {ING.GROUPS[g2][0]}" if g2 in ING.GROUPS else "")
        if c1.checkbox(label, key=tick_key):
            pct = c2.number_input(f"% of dry weight ({ING.name(i)})", 0.0, 60.0, step=0.5, key=pct_key,
                                  label_visibility="collapsed")
            chosen.append({"ingredient": i, "name": ING.name(i), "pct": float(pct)})
        else:
            c2.caption(f"{ss[pct_key]:g} % of dry weight")

# 4. mix C:N and water, recalculated on every change
supp_pct = sum(c["pct"] for c in chosen)
mix = None
if supp_pct >= 100:
    st.error(f"The ticked supplements add up to {supp_pct:g} % of the dry mix; lower them so the main material "
             "keeps a share. The guide's own mix is used until then.")
else:
    mix = {"main_name": substrate, "supplements": [{"name": c["name"], "pct": c["pct"]} for c in chosen]}
parts = {**({main: 100 - supp_pct} if main != OTHER else {}), **{c["ingredient"]: c["pct"] for c in chosen}}
cn = ING.mix_cn(parts) if main != OTHER else None      # without the bulk the ratio would mislead
moisture = float(guide_row["substrate_moisture_pct"])
m1, m2 = st.columns(2)
m1.metric("Mix C:N (estimate)", "n/a" if cn is None else f"{cn:.0f}:1",
          help="Sum of weight × C% over sum of weight × N% of the dry ingredients; spawn not counted.")
m2.metric("Water to add per container", f"{recipe_maths.water_to_add(kg_plan, moisture) * HANDLING:.2f} kg",
          help=f"Brings the mix to {moisture:g} % moisture; 5% extra for handling.")
if ING.uses_category_values(parts):
    st.caption("(some values are typical for their category)")

ss["recipe"] = {"substrate": substrate_code, "spawn_pct": pipeline.SPAWN_PCT, "method": method,
                "protocol_id": ING.METHODS[method][1], "jar_size": jar_size, "autoclave_min": autoclave_min,
                "main": None if main == OTHER else main, "supplements": chosen, "mix": mix, "mix_cn": cn}
result = flow.run()
batch = flow.get_batch()
what = flow.choice_label()

# --- recipe ---------------------------------------------------------------------------------
st.subheader("Amounts to weigh")
rv = result.recipe.value
rec, n = rv["rec"], rv["n"]
pc = rec["per_container"]
h = HANDLING
ing = pd.DataFrame([{"Ingredient": i["name"], "Per container (kg)": i["kg"] * h, "Total (kg)": i["kg"] * n * h}
                    for i in rec["ingredients"]]
                   + [{"Ingredient": f"Water (to {rec['moisture_pct']:g} % moisture)", "Per container (kg)": pc["water"] * h,
                       "Total (kg)": pc["water"] * n * h},
                      {"Ingredient": f"Spawn ({rv['spawn_pct']:g} % of the whole mix)", "Per container (kg)": pc["spawn"] * h,
                       "Total (kg)": pc["spawn"] * n * h}])
st.dataframe(ing.style.format({"Per container (kg)": "{:.2f}", "Total (kg)": "{:.2f}"}), hide_index=True)
st.caption("5% extra on everything is included here for handling")
st.caption("Water assumes the dry ingredients already hold about 10% water. Supplement amounts start at the middle "
           f"of the guide's range ({rec['supplementation'] or 'none listed'}).")
if rec["supplements_text_only"]:
    st.caption("Also from the guide: " + "; ".join(rec["supplements_text_only"]) + ".")
st.caption(f"Guide row {rec['row_note']}")
if flow.is_materials():
    st.caption(result.recipe.note)

# --- stage timeline (the Stage 1 block below is the fallback) -------------------------------------
est, fc, dates = result.colonisation_estimate, result.colonisation_forecast, result.dates


def logistic(x, t90, c0=0.02, c90=0.90, start=0.0):
    """Logistic through (start, c0) and (t90, c90); x in days."""
    def logit(c):
        return math.log(c / (1 - c))
    k = (logit(c90) - logit(c0)) / (t90 - start)
    mid = t90 - logit(c90) / k
    return [100 / (1 + math.exp(-k * (xi - mid))) for xi in x]


def colonisation_chart():
    """% colonised against days: dotted = estimate (S-curve assumed), solid = measured photos."""
    if est.is_preview or est.value is None:
        return
    photos = sorted((p for p in batch.photos if p.day >= 0 and not p.quality), key=lambda p: p.day)
    t90 = float(est.value["typical"])
    if photos and fc.value is not None and fc.value.get("method") in ("curve fit", "consensus update"):
        t90 = float(fc.value["day90"])                      # Colonisation forecast (3 or more photos)
    if not t90 > 0:
        return
    fig = go.Figure()
    if not photos:
        xs = [t90 * i / 60 for i in range(0, 76)]
        fig.add_trace(go.Scatter(x=xs, y=logistic(xs, t90), mode="lines", line=dict(dash="dot", color=STAGE_COLOR),
                                 name="Estimate"))
    else:
        pd_, pc = [p.day for p in photos], [100 * p.coverage for p in photos]
        fig.add_trace(go.Scatter(x=[0] + pd_, y=[0] + pc, mode="lines", line=dict(color=STAGE_COLOR),
                                 name="Measured", hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=pd_, y=pc, mode="markers", marker=dict(size=9, color=STAGE_COLOR), name="Photos",
                                 hovertemplate="day %{x}: %{y:.0f}%<extra></extra>"))
        last_d, last_c = pd_[-1], min(max(pc[-1], 2.0), 98.0)
        if last_c < 90 and t90 > last_d:
            xs = [last_d + (t90 * 1.25 - last_d) * i / 60 for i in range(61)]
            ys = logistic(xs, t90, c0=last_c / 100, start=last_d)
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(dash="dot", color=STAGE_COLOR),
                                     name="Forecast"))
    fig.add_hline(y=90, line_dash="dot", line_color="#9aa0a6", annotation_text="90%")
    fig.add_vline(x=t90, line_dash="dot", line_color="#9aa0a6", annotation_text=f"day {t90:.0f}")
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=40), xaxis_title="Days since inoculation",
                      yaxis_title="% colonised", yaxis=dict(range=[0, 100]), showlegend=False)
    st.subheader("Colonisation")
    st.plotly_chart(fig, use_container_width=True)
    src = "the Colonisation forecast" if t90 != float(est.value["typical"]) else "the Colonisation time estimate"
    st.caption(f"Dotted: {src} (90% on day {t90:.0f}). The S-curve shape is our assumption. "
               + ("Solid: measured from your photos in Monitor." if photos else
                  "Photos added in Monitor are drawn as points with a solid line.")
               + " If the temperature changes, the estimate is re-run and the dotted part moves.")


colonisation_chart()

base = pipeline.baseline_row(batch)
if base is not None:
    r, row_note = base
    temp = ss["temp_c"]
    species = r["species"]
    st.subheader("Stage timeline")
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

    # --- horizontal timeline: events (markers) and stages (bars) ---------------------------------
    fig = go.Figure()
    for name, x0, x1, color in (("Colonising", 0, ind_day, STAGE_COLOR), ("Fruiting", ind_day, har_day, STAGE_COLOR)):
        fig.add_trace(go.Bar(y=["Timeline"], x=[x1 - x0], base=[x0], orientation="h", name=name, width=0.35,
                             marker_color=color, opacity=0.45 if name == "Colonising" else 0.7,
                             text=name, textposition="inside", insidetextanchor="middle",
                             hovertemplate=f"{name}: day {x0:g}–{x1:g}<extra></extra>"))
    for name, day in (("Inoculation", 0), ("Induction", ind_day), ("Harvest", har_day)):
        fig.add_trace(go.Scatter(x=[day], y=["Timeline"], mode="markers+text", name=name,
                                 marker=dict(symbol="line-ns", size=36, line=dict(width=3, color=EVENT_COLOR)),
                                 text=[f"{name}<br>day {int(day)}"], textposition="top center"))
    fig.update_layout(height=230, margin=dict(l=10, r=10, t=30, b=40), xaxis_title="Days since inoculation",
                      showlegend=False, barmode="overlay")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Bars: stages. Ticks: events, on the typical day. Induction falls on the typical day colonisation ends; "
               "Harvest is the typical first-harvest day counted from the start of induction.")

    # --- cards: events (blue border) and stages (green border) -----------------------------------
    NIG = "not in guide"

    def val(x, unit=""):
        return NIG if str(x) in ("", "nan", "None") else f"{x}{unit}"

    def rng(lo, hi, unit):
        return NIG if str(lo) == "nan" or str(hi) == "nan" else (f"{lo:g}–{hi:g}{unit}" if lo != hi else f"{lo:g}{unit}")

    def card(color, title, line, text="", note=""):
        body = f"<b>{html.escape(title[0])}</b> · {html.escape(title[1])}<br>{html.escape(line)}"
        if text:
            body += f"<br>{html.escape(text)}"
        if note:
            body += f"<br><small style='opacity:0.7'>{html.escape(note)}</small>"
        st.markdown(f"<div style='border:2px solid {color}; border-left:8px solid {color}; border-radius:8px; "
                    f"padding:0.6rem 0.9rem; margin:0.4rem 0;'>{body}</div>", unsafe_allow_html=True)

    inc_t = rng(r["incubation_temp_min_C"], r["incubation_temp_max_C"], " °C")
    inc_rh = val(r["incubation_RH_pct"], " %")
    fr_t = rng(r["fruiting_temp_min_C"], r["fruiting_temp_max_C"], " °C")
    fr_rh = rng(r["fruiting_RH_min_pct"], r["fruiting_RH_max_pct"], " %")
    light = val(t["induction_light_action"])

    def conds(temp, rh, lt):
        return f"🌡️ {temp} · 💧 {rh} · 💡 {lt}"

    def span(label):
        s_ = tl.loc[label]
        return f"day {s_['start_day']}–{s_['end_day']} (typical {s_['typical_day']})"

    prep = val(t["preparation_actions"]) if str(t["preparation_actions"]) != "nan" else \
        "Mix spawn into the cooled substrate and seal."
    induct = val(t["induction_actions"]) if str(t["induction_actions"]) != "nan" else \
        "Move to fruiting conditions, open the bag, give light and fresh air."
    card(EVENT_COLOR, ("Inoculation", "day 0"), conds(inc_t, inc_rh, NIG), prep)
    card(STAGE_COLOR, ("Colonising", f"day {col_days['min']}-{col_days['max']} (typical {col_days['typical']})"),
         conds(inc_t, inc_rh, NIG))
    card(EVENT_COLOR, ("Induction", f"day {ind_day:g}"), conds(fr_t, fr_rh, light), induct,
         note=flow.FULLY_COLONISED_NOTE)
    card(STAGE_COLOR, ("Fruiting", f"day {ind_row['start_day']}-{har_row['end_day']} "
                       f"(typical {ind_day:g}-{har_day:g})"), conds(fr_t, fr_rh, light))
    card(EVENT_COLOR, ("Harvest", f"day {har_day:g}"), conds(fr_t, fr_rh, NIG),
         "Pick when cap edges flatten, before spores drop.")
    if species == "Lentinula edodes":
        st.info(f"Unresolved: {t['requirements_unresolved']}")

    st.caption(f"Source: {col['source']} · evidence: {r['evidence_type']} · confidence: {col['confidence']}. "
               f"Row used: {row_note}. Consensus values, not a prediction.")
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
