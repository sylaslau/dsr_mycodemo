"""Part C (11-18), 5-page flow: induction steps on Recipe and actions (was page 7); Step n of 5. The fruiting
record (was page 8) is tested in test_monitor_stages."""

from datetime import date, timedelta
from pathlib import Path

from dsr_mycodemo import pipeline
from dsr_mycodemo.cultivation import baseline_guide as bg
from dsr_mycodemo.pipeline import Batch

APP = Path(__file__).parents[1] / "dsr_mycodemo/app"
START = date(2026, 10, 8)
PLAN = {"batch_label": "B1", "species": "Pleurotus ostreatus", "inoc_date": START, "n_containers": 2,
        "temp_c": 24.0, "substrate": "sawdust", "spawn_pct": 10.0}


def _page(name, goal="Food", choice="Pleurotus ostreatus", **state):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(APP / "pages" / name), default_timeout=60)
    s = at.session_state
    s["goal"], s["choice"], s["temp_c"], s["inoc_date"] = goal, choice, 24.0, START
    s["environment"], s["env_where"] = "Small plastic container (about 1 L)", "Plastic container"
    for k, v in state.items():
        s[k] = v
    at.run()
    assert not at.exception, at.exception
    return at


def _steps(**state):
    """Recipe and actions with the induction / post-treatment steps shown (was page 7)."""
    return _page("2_Recipe_and_actions.py", show_next_steps=True, **state)


def _md(at):
    return " ".join(m.value for m in at.markdown)


def _bubbles(at):
    return [m.value for m in at.markdown if "border-left:8px" in m.value]


# --- pipeline -------------------------------------------------------------------------------------
def test_fruiting_dates_are_consensus_days_from_the_start():
    b = Batch(goal="Food", choice="Pleurotus ostreatus", inoc_date=START)
    f = pipeline.fruiting_estimate(b).value
    step = pipeline.fruiting_dates(b, date(2026, 11, 1))
    assert step.value == [("Start of induction", date(2026, 11, 1)),
                          ("Pinning", date(2026, 11, 1) + timedelta(days=f["days_to_pinning"])),
                          ("First harvest", date(2026, 11, 1) + timedelta(days=f["first_harvest"]))]
    assert "Consensus days" in step.note and "Not a model" in step.note
    assert pipeline.fruiting_dates(Batch(goal="Food", choice="Custom"), date(2026, 11, 1)).is_preview
    assert pipeline.fruiting_dates(b, None).value == []


def test_next_stage_ranges_food_from_the_guide_materials_none():
    b = Batch(goal="Food", choice="Pleurotus ostreatus")
    r, _ = pipeline.baseline_row(b)
    f = bg.fruiting(r)
    rng = pipeline.next_stage_ranges(b)
    assert rng["temp"][:2] == (f["fruiting_temp_C"]["min"], f["fruiting_temp_C"]["max"])
    assert rng["rh"][:2] == (f["fruiting_rh_pct"]["min"], f["fruiting_rh_pct"]["max"])
    assert rng["co2"][1] == f["co2_max_ppm"]
    assert pipeline.next_stage_ranges(Batch(goal="Materials")) is None
    assert pipeline.next_stage_ranges(Batch(goal="Food", choice="Custom")) is None


# --- step headers and titles ----------------------------------------------------------------------
def test_five_pages_in_order_with_plain_headers():   # no "Step n of 5" line any more (11-19)
    pages = sorted((APP / "pages").glob("[0-9]_*.py"))
    assert [f.name for f in pages] == ["1_Start_a_batch.py", "2_Recipe_and_actions.py", "3_Timeline.py",
                                       "4_Monitor.py", "5_Check_image.py"]
    for f in pages:
        src = f.read_text()
        assert "step_header" not in src and "flow.header(" in src, f.name


# --- induction steps on Recipe and actions (was page 7) --------------------------------------------------------------------------------
def test_induction_page_shows_steps_bubbles_check_and_dates():
    at = _steps(batch=PLAN)
    r, _ = pipeline.baseline_row(Batch(goal="Food", choice="Pleurotus ostreatus"))
    acts = bg.fruiting(r)["induction_actions"]
    text = _md(at)
    for key in ("overview", "light", "fresh_air", "humidity"):
        assert acts[key] in text, key
    assert [b.split("</b>")[0].split("<b>")[1] for b in _bubbles(at)] == ["Induction", "Fruiting", "Harvest"]
    assert [m.label for m in at.metric][-3:] == ["Start of induction", "Pinning", "First harvest"]
    assert any("Consensus days" in c.value and "Not a model" in c.value for c in at.caption)
    assert "Temperature" in text and "not entered" in text                 # conditions check with no reading yet


def test_start_date_is_the_typed_fully_colonised_date():
    typed = date(2026, 10, 25)
    at = _steps(batch=PLAN, outcomes={"B1-01": {"colonised": date(2026, 10, 23), "mould": False},
                                                         "B1-02": {"colonised": typed, "mould": False}})
    assert at.date_input(key="plan_next_start").value == typed
    assert any("Fully colonised on" in c.value and "2 sample(s)" in c.value for c in at.caption)


def test_start_date_falls_back_to_the_induction_marker():
    at = _steps(batch=PLAN)
    assert at.date_input(key="plan_next_start").value is not None
    assert any(pipeline.MARKER_LABEL in c.value for c in at.caption)


def test_residence_for_the_next_stage_is_saved_separately():
    at = _steps(batch=PLAN)
    at.button(key="next_where_Tent or Cabinet").click().run()
    assert at.session_state["residences"]["next"] == "Tent or Cabinet"
    assert at.session_state["env_where"] == "Plastic container"            # colonisation residence unchanged
    assert at.session_state["batch"] == PLAN                               # the plan is not cleared


def test_conditions_check_reads_the_next_residence():
    reading = {"temp": 40.0, "rh": 90.0, "co2": 800.0, "datetime": "2026-10-30T08:00"}
    at = _steps(batch=PLAN, residences={"next": "Tent or Cabinet"},
               monitor_env={"Tent or Cabinet": reading})
    text = _md(at)
    assert "40 °C" in text and "#F12430" in text                             # too hot = red
    assert any("Latest reading in Tent or Cabinet" in c.value for c in at.caption)


def test_next_step_button_toggles_the_induction_section():
    at = _page("2_Recipe_and_actions.py", batch=PLAN)
    btn = at.button(key="show_next_steps_btn")
    assert btn.label == "Show induction steps" and "Induction steps" not in [s.value for s in at.subheader]
    btn.click().run()
    assert at.session_state["show_next_steps"] is True
    assert "Induction steps" in [s.value for s in at.subheader]
    assert at.button(key="show_next_steps_btn").label == "Hide induction steps"
    at.button(key="show_next_steps_btn").click().run()
    assert "Induction steps" not in [s.value for s in at.subheader]


def test_confirmed_start_from_monitor_replaces_the_date_input():
    at = _steps(batch=PLAN, batch_stage="Fruiting", next_start=date(2026, 11, 2))
    assert not any(d.key == "plan_next_start" for d in at.date_input)
    assert "**Start of induction:** 02 Nov 2026" in _md(at)
    assert at.metric[-3].value == "02 Nov"
