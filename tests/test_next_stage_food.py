"""Part C (11-18): page 7 Induction and page 8 Monitor fruiting (Food); titles switch by mode; Step n of 8."""

from datetime import date, timedelta
from pathlib import Path

import pytest

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
def test_every_page_says_step_n_of_8():
    for f in sorted((APP / "pages").glob("[1-8]_*.py")):
        src = f.read_text()
        assert "step_header(" in src and ", 8, " in src.split("step_header(")[1].split("\n")[0], f.name


@pytest.mark.parametrize("goal, choice, t7, t8", [("Food", "Pleurotus ostreatus", "Induction", "Monitor fruiting"),
                                                  ("Materials", "Foam", "Post-treatment", "Monitor post-treatment")])
def test_titles_follow_the_mode(goal, choice, t7, t8):
    at7 = _page("7_Next_stage.py", goal, choice)
    assert at7.title[0].value == t7 and "Step 7 of 8" in _md(at7)
    at8 = _page("8_Monitor_next_stage.py", goal, choice)
    assert at8.title[0].value == t8 and "Step 8 of 8" in _md(at8)


# --- page 7 Induction --------------------------------------------------------------------------------
def test_induction_page_shows_steps_bubbles_check_and_dates():
    at = _page("7_Next_stage.py", batch=PLAN)
    r, _ = pipeline.baseline_row(Batch(goal="Food", choice="Pleurotus ostreatus"))
    acts = bg.fruiting(r)["induction_actions"]
    text = _md(at)
    for key in ("overview", "light", "fresh_air", "humidity"):
        assert acts[key] in text, key
    assert [b.split("</b>")[0].split("<b>")[1] for b in _bubbles(at)] == ["Induction", "Fruiting", "Harvest"]
    assert [m.label for m in at.metric] == ["Start of induction", "Pinning", "First harvest"]
    assert any("Consensus days" in c.value and "Not a model" in c.value for c in at.caption)
    assert "Temperature" in text and "not entered" in text                 # conditions check with no reading yet


def test_start_date_is_the_typed_fully_colonised_date():
    typed = date(2026, 10, 25)
    at = _page("7_Next_stage.py", batch=PLAN, outcomes={"B1-01": {"colonised": date(2026, 10, 23), "mould": False},
                                                         "B1-02": {"colonised": typed, "mould": False}})
    assert at.date_input(key="next_start").value == typed
    assert any("Fully colonised on" in c.value and "2 sample(s)" in c.value for c in at.caption)


def test_start_date_falls_back_to_the_induction_marker():
    at = _page("7_Next_stage.py", batch=PLAN)
    assert at.date_input(key="next_start").value is not None
    assert any(pipeline.MARKER_LABEL in c.value for c in at.caption)


def test_residence_for_the_next_stage_is_saved_separately():
    at = _page("7_Next_stage.py", batch=PLAN)
    at.button(key="next_where_Tent or Cabinet").click().run()
    assert at.session_state["residences"]["next"] == "Tent or Cabinet"
    assert at.session_state["env_where"] == "Plastic container"            # colonisation residence unchanged
    assert at.session_state["batch"] == PLAN                               # the plan is not cleared


def test_conditions_check_reads_the_next_residence():
    reading = {"temp": 40.0, "rh": 90.0, "co2": 800.0, "datetime": "2026-10-30T08:00"}
    at = _page("7_Next_stage.py", batch=PLAN, residences={"next": "Tent or Cabinet"},
               monitor_env_next={"Tent or Cabinet": reading})
    text = _md(at)
    assert "40 °C" in text and "#F12430" in text                             # too hot = red
    assert any("Latest reading in Tent or Cabinet" in c.value for c in at.caption)


# --- page 8 Monitor fruiting ----------------------------------------------------------------------------
def test_monitor_fruiting_uses_the_next_residence_and_saves_its_own_log():
    at = _page("8_Monitor_next_stage.py", batch=PLAN)
    assert at.subheader[0].value == "Monotub or Plastic Container"          # next empty = colonisation residence
    at.button(key="next_mon_save_Plastic container").click().run()
    saved = at.session_state["monitor_env_next"]["Plastic container"]
    assert len(saved["log"]) == 1 and saved["day"] is not None
    assert "Plastic container" not in at.session_state["monitor_env"]     # Monitor's own log untouched


def test_monitor_fruiting_records_flushes_and_shows_harvest_readiness_preview():
    at = _page("8_Monitor_next_stage.py", batch=PLAN)
    assert at.selectbox(key="next_sample").options == ["B1-01", "B1-02"]
    assert "Harvest readiness" in _md(at) and "PREVIEW" in _md(at)
    at.number_input(key="next_h_g_B1-01").set_value(120.0).run()
    at.button(key="next_h_add_B1-01").click().run()
    assert at.session_state["harvest"]["B1-01"][0]["g"] == 120.0


def test_monitor_fruiting_without_residence_links_back():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(APP / "pages/8_Monitor_next_stage.py"), default_timeout=60)
    at.session_state["goal"], at.session_state["choice"] = "Food", "Pleurotus ostreatus"
    at.run()
    assert not at.exception
    assert any("Choose the residence on Induction first" in i.value for i in at.info)
