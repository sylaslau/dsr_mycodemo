"""5-page flow (11-18): Monitor has one box per residence with one reading log each; the batch stage changes only
through the grower's confirm button; the sample record follows the stage."""

from datetime import date, timedelta
from pathlib import Path

APP = Path(__file__).parents[1] / "dsr_mycodemo/app"
START = date(2026, 10, 8)
FOOD_PLAN = {"batch_label": "B1", "species": "Pleurotus ostreatus", "inoc_date": START, "n_containers": 2,
             "temp_c": 24.0, "substrate": "sawdust", "spawn_pct": 10.0}
MAT_PLAN = {"batch_label": "M1", "species": "Trametes versicolor", "inoc_date": START, "n_containers": 2,
            "temp_c": 24.0, "substrate": "hemp_hurd", "spawn_pct": 10.0}


def _monitor(goal="Food", plan=FOOD_PLAN, **state):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(APP / "pages/3_Monitor.py"), default_timeout=60)
    s = at.session_state
    s["goal"], s["choice"], s["temp_c"], s["inoc_date"] = goal, "Pleurotus ostreatus" if goal == "Food" else "Foam", 24.0, START
    s["material_species"] = "Trametes versicolor"
    s["environment"], s["env_where"] = "Small plastic container (about 1 L)", "Plastic container"
    s["batch"] = plan
    for k, v in state.items():
        s[k] = v
    at.run()
    assert not at.exception, at.exception
    return at


def _subheaders(at):
    return [h.value for h in at.subheader]


def _box_of_batch(at):
    """The residence box that holds the batch bubble (the one with the sample select)."""
    return [sb.key.removeprefix("sample_") for sb in at.selectbox if sb.key and sb.key.startswith("sample_")]


def _current(at):
    import re
    html_ = " ".join(m.value for m in at.markdown)
    return re.findall(r"#fff;[^>]*><b>([^<]+)</b>", html_)


# --- stage only through the confirm button --------------------------------------------------------
def test_stage_starts_colonising_and_does_not_follow_the_dates():
    at = _monitor(plan={**FOOD_PLAN, "inoc_date": START - timedelta(days=200)},
                  residences={"next": "Tent or Cabinet"})       # dates say long past harvest
    assert at.session_state["batch_stage"] == "Colonising" and _current(at) == ["Colonising"]
    assert "next_start" not in at.session_state
    assert any("Dates say: ready for induction since" in c.value for c in at.caption)


def test_confirm_button_sets_stage_date_and_moves_the_bubble():
    at = _monitor(residences={"next": "Tent or Cabinet"})
    assert _subheaders(at)[:2] == ["Monotub or Plastic Container", "Tent or Cabinet"]
    assert _box_of_batch(at) == ["Plastic container"]
    btn = at.button(key="confirm_next")
    assert btn.label == "Confirm induction started"
    at.date_input(key="confirm_date").set_value(date(2026, 10, 30))
    btn.click().run()
    s = at.session_state
    assert s["batch_stage"] == "Fruiting" and s["next_start"] == date(2026, 10, 30)
    assert _box_of_batch(at) == ["Tent or Cabinet"] and _current(at) == ["Fruiting"]
    assert not any(b.key == "confirm_next" for b in at.button)
    at.button(key="mark_harvested").click().run()
    assert at.session_state["batch_stage"] == "Harvested"


def test_without_a_next_residence_the_button_opens_the_steps():
    at = _monitor()
    assert at.button(key="confirm_next").label == "Confirm induction started"
    assert not any(d.key == "confirm_date" for d in at.date_input)
    assert any("Recipe and actions" in c.value for c in at.caption)
    at.button(key="confirm_next").click().run()
    assert at.session_state["batch_stage"] == "Colonising" and "next_start" not in at.session_state
    assert at.session_state["show_next_steps"] is True


def test_contaminated_at_any_stage():
    at = _monitor()
    at.button(key="mark_contaminated").click().run()
    assert at.session_state["batch_stage"] == "Contaminated"
    assert not any(b.key in ("mark_contaminated", "confirm_next") for b in at.button)


def test_materials_confirm_post_treatment():
    at = _monitor("Materials", MAT_PLAN, residences={"next": "Oven"})
    html_ = " ".join(m.value for m in at.markdown)
    assert all(w in html_ for w in ("Colonisation", "Post-treatment", "Contaminated"))
    at.button(key="confirm_next").click().run()
    assert at.session_state["batch_stage"] == "Post-treatment" and _box_of_batch(at) == ["Oven"]
    assert not any(b.key == "mark_harvested" for b in at.button)


# --- one reading log per residence ---------------------------------------------------------------------
def test_one_reading_log_per_residence_whatever_the_stage():
    at = _monitor(residences={"next": "Tent or Cabinet"}, batch_stage="Fruiting", next_start=date(2026, 10, 30))
    saves = [b.key for b in at.button if b.label == "Save"]
    assert saves == ["mon_save_Plastic container", "mon_save_Tent or Cabinet"]
    at.button(key="mon_save_Tent or Cabinet").click().run()
    at.button(key="mon_save_Plastic container").click().run()
    env = at.session_state["monitor_env"]
    assert len(env["Tent or Cabinet"]["log"]) == 1 and len(env["Plastic container"]["log"]) == 1
    assert "monitor_env_next" not in at.session_state or not at.session_state["monitor_env_next"]


def test_box_ranges_follow_the_stage_of_the_batch_in_it():
    from dsr_mycodemo import pipeline
    from dsr_mycodemo.pipeline import Batch
    at = _monitor(residences={"next": "Tent or Cabinet"}, batch_stage="Fruiting", next_start=date(2026, 10, 30))
    fr = pipeline.next_stage_ranges(Batch(goal="Food", choice="Pleurotus ostreatus"))
    assert at.number_input(key="mon_temp_Tent or Cabinet_fruit").value == float(fr["temp"][2])
    assert any(n.key == "mon_temp_Plastic container_grow" for n in at.number_input)     # no batch: colonisation
    assert any("fruiting ranges" in c.value for c in at.caption)


def test_post_treatment_box_is_a_record_with_temperature_and_humidity():
    at = _monitor("Materials", MAT_PLAN, residences={"next": "Oven"}, batch_stage="Post-treatment",
                  next_start=date(2026, 11, 1))
    keys = {n.key for n in at.number_input}
    assert "mon_temp_Oven_post" in keys and "mon_rh_Oven_post" in keys
    assert not any(k and k.startswith("mon_co2_Oven") for k in keys)
    assert any("record only" in c.value for c in at.caption)


# --- sample record per stage ------------------------------------------------------------------------------
def test_colonising_record_has_colonised_date_and_mould_only():
    at = _monitor()
    keys = {w.key for w in (*at.date_input, *at.checkbox, *at.number_input)}
    assert "o_col_B1-01" in keys and "o_mould_B1-01" in keys
    assert not any(k and "h_g_" in k for k in keys)


def test_fruiting_record_has_photo_harvest_readiness_and_flushes():
    at = _monitor(residences={"next": "Tent or Cabinet"}, batch_stage="Fruiting", next_start=date(2026, 10, 30))
    html_ = " ".join(m.value for m in at.markdown)
    assert "Harvest readiness" in html_ and "PREVIEW" in html_
    at.number_input(key="next_h_g_B1-01").set_value(120.0).run()
    at.button(key="next_h_add_B1-01").click().run()
    assert at.session_state["harvest"]["B1-01"][0]["g"] == 120.0


def test_post_treatment_record_has_weight_log_and_dry_check():
    d = date(2026, 11, 1)
    log = [{"date": d + timedelta(days=i), "g": g} for i, g in enumerate((200, 150, 149, 148.5))]
    at = _monitor("Materials", MAT_PLAN, residences={"next": "Oven"}, batch_stage="Post-treatment",
                  next_start=d, weights={"M1-01": log})
    assert "M1-01 is dry" in " ".join(s.value for s in at.success)
    assert any("Project rule" in c.value for c in at.caption)
