"""Timeline: the colonisation curve and stage timeline in one figure, the stage bubbles and the dates (moved from
Recipe), the fruiting dates once induction is confirmed on Monitor; below, the calendar and tasks previews."""

import math

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from dsr_mycodemo import pipeline
from dsr_mycodemo.app import flow, stage_ui
from dsr_mycodemo.cultivation import baseline_guide as bg

st.set_page_config(page_title="Timeline", page_icon="📅", layout="wide")
flow.init()
ss = st.session_state
flow.need("batch", "Recipe and actions", "pages/3_Recipe_and_timeline.py")

EVENT_COLOR, STAGE_COLOR = stage_ui.EVENT_COLOR, stage_ui.STAGE_COLOR
flow.step_header(6, 8, "Timeline")
batch = flow.sample_batch()
result = pipeline.run(batch)

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
if flow.is_materials():
    st.subheader("Colonisation and timeline")
    stage_ui.materials_timing_previews()
elif base is None:
    st.subheader("Colonisation")
    if col_setup:
        draw(col_setup, None)
    stage_ui.colonisation_days(result)
else:
    r, _ = base
    st.subheader("Colonisation and stage timeline")
    stage_ui.temperature_line(r, batch.temp_c)
    tl = bg.stages(r).set_index("stage")
    draw(col_setup, (tl.loc["Start induction", "typical_day"], tl.loc["First harvest", "typical_day"]))
    stage_ui.stage_cards(r)           # stage bubbles, one row: name · days, then temperature, humidity, CO2, light
    if r["species"] == "Lentinula edodes":
        t = bg.load_text()
        st.info(f"Unresolved: {t[t['ref_id'] == r['ref_id']].iloc[0]['requirements_unresolved']}")
    stage_ui.colonisation_days(result)

# --- fruiting dates once induction is confirmed on Monitor (consensus days, not a model) -------------------
start = stage_ui.confirmed_start()
if start and not flow.is_materials():
    st.subheader("Fruiting dates")
    fd = pipeline.fruiting_dates(batch, start)
    if fd.value:
        for col, (label, day) in zip(st.columns(len(fd.value)), fd.value):
            col.metric(label, day.strftime("%d %b"), help="Consensus days from the guide, not a model")
    st.caption(fd.note)

# --- calendar and tasks (previews) -----------------------------------------------------------------
st.divider()
dates = result.dates
if dates.value:
    rows = "".join(f"<tr><td>{a.strftime('%a %d %b')}"
                   f"{'' if a == b else ' – ' + b.strftime('%a %d %b')}</td><td>{name}</td></tr>"
                   for name, a, b in dates.value)
    body = f"Predicted dates from your plan:<table>{rows}</table>Source: {dates.source}. {dates.note}"
else:
    body = dates.note
flow.preview("Calendar", body)
if result.warnings.is_preview:
    flow.preview(result.warnings.name, result.warnings.note)
for w in result.warnings.value:
    st.warning(w)
flow.preview("Tasks and reminders", "Watering, checking the photos, starting post-treatment: reminders on your phone.")
st.button("Add to my calendar", disabled=True)
st.button("Send me reminders", disabled=True)
