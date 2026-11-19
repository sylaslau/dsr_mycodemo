"""Page clean-up card (11-10): no small captions on Environment, messages under their sliders, primary Next buttons,
Recipe page without form/source captions or yield/harvest-readiness boxes, Monitor date-time and CO2 unknown."""

from datetime import date, datetime, time
from pathlib import Path

from dsr_mycodemo import pipeline

APP = Path(__file__).parents[1] / "dsr_mycodemo/app"
START = date(2026, 10, 8)


def _page(name):
    from streamlit.testing.v1 import AppTest
    return AppTest.from_file(str(APP / name), default_timeout=60)


def _all_text(at):
    return " ".join([m.value for m in at.markdown] + [c.value for c in at.caption]
                    + [x.value for x in (*at.info, *at.success, *at.warning)])


# --- Environment ---------------------------------------------------------------------------
def test_environment_has_no_captions_and_messages_sit_under_their_sliders():
    at = _page("pages/1_Start_a_batch.py")
    at.session_state["goal"], at.session_state["choice"] = "Food", "Blue Oyster"
    at.session_state["environment"], at.session_state["env_where"] = "Room", "Room or Chamber"
    at.run()
    assert not at.exception
    text = _all_text(at)
    assert "Row used" not in text and "Fruiting later" not in text and "We plan" not in text
    assert len(at.caption) == 2          # only the Residence and Vessels definitions
    # conditions row: the second set of two columns holds slider + message each
    t_col, h_col = [c for c in at.columns if c.slider][:2]
    assert t_col.slider[0].label.startswith("Temperature") and (t_col.success or t_col.warning)
    assert h_col.slider[0].label.startswith("Humidity") and (h_col.success or h_col.warning)
    nxt = at.button(key="next")
    assert nxt.label == "Next: recipe and actions" and nxt.proto.type == "primary"


def test_start_page_shows_the_environment_once_a_choice_exists():
    at = _page("pages/1_Start_a_batch.py")
    at.run()
    assert not at.exception
    assert "Step 2. Describe your growth environment" not in [h.value for h in at.header] and not any(b.key == "next" for b in at.button)
    at.session_state["goal"], at.session_state["choice"] = "Food", "Blue Oyster"
    at.run()
    assert [h.value for h in at.header] == ["Step 1. Pick what you want to grow", "Step 2. Describe your growth environment", "Conditions"]
    assert "Residence" in [s.value for s in at.subheader] and at.slider[0].label == "Temperature (°C)"
    assert not any(b.key == "next" for b in at.button)                  # no residence yet
    assert any("Choose where you grow" in c.value for c in at.caption)
    at.button(key="where_Tent or Cabinet").click().run()
    assert at.session_state["environment"] == "Shelf or grow tent"
    assert at.button(key="next").label == "Next: recipe and actions"


# --- Recipe and timeline -------------------------------------------------------------------
def test_recipe_page_drops_form_and_source_captions_and_yield_box():
    at = _page("pages/2_Recipe_and_actions.py")
    s = at.session_state
    s["goal"], s["choice"], s["temp_c"] = "Food", "Pleurotus ostreatus", 22.0
    s["environment"], s["env_where"] = "Small plastic container (about 1 L)", "Plastic container"
    s["rc_method"] = "STER"
    at.run()
    assert not at.exception
    text = _all_text(at)
    for gone in ("Source:", "Row used", "Yield: record your harvest", "Harvest readiness", "particles under"):
        assert gone not in text, gone
    assert sum("Weight of mix for each vessel" in m.value for m in at.markdown) == 1


# --- Monitor -------------------------------------------------------------------------------
def test_reading_with_chosen_date_gets_its_day():
    e = pipeline.reading_entry({"temp": 22.0, "rh": 85.0, "co2": 900.0}, "Sensor",
                               datetime.combine(date(2026, 10, 15), time(9, 30)), START)
    assert e["day"] == 7 and e["datetime"] == "2026-10-15T09:30" and e["co2"] == 900.0
    assert pipeline.reading_entry({"temp": 22.0}, "Guess", datetime(2026, 10, 15, 9, 30))["day"] is None


def test_co2_unknown_saves_empty():
    e = pipeline.reading_entry({"temp": 22.0, "rh": 85.0, "co2": 900.0}, "Sensor", datetime(2026, 10, 9, 8, 0),
                               START, co2_unknown=True)
    assert e["co2"] is None and e["day"] == 1


def _monitor():
    at = _page("pages/4_Monitor.py")
    at.session_state["goal"], at.session_state["choice"] = "Food", "Blue Oyster"
    at.session_state["env_where"], at.session_state["env_size"] = "Tent or Cabinet", {"Tent or Cabinet": 1.0}
    at.session_state["batch"] = {"batch_label": "B1", "species": "Pleurotus ostreatus", "inoc_date": START,
                                 "n_containers": 2, "temp_c": 24.0, "substrate": "sawdust", "spawn_pct": 10.0}
    at.run()
    assert not at.exception
    return at


def test_monitor_entry_uses_chosen_date_time_and_co2_unknown_goes_grey():
    at = _monitor()
    name = "Tent or Cabinet"
    at.date_input(key=f"mon_date_{name}").set_value(date(2026, 10, 18))
    at.time_input(key=f"mon_time_{name}").set_value(time(7, 45))
    at.checkbox(key=f"mon_co2_unknown_{name}").check().run()
    assert any("#9E9E9E" in m.value and "unknown" in m.value for m in at.markdown)       # grey CO2 bubble
    at.button(key=f"mon_save_{name}").click().run()
    assert not at.exception
    saved = at.session_state["monitor_env"][name]
    assert saved["co2"] is None and saved["datetime"] == "2026-10-18T07:45" and saved["day"] == 10
    assert len(saved["log"]) == 1
