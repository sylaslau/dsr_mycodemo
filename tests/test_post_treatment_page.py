"""Part E (11-18), 5-page flow: post-treatment steps on Recipe and actions (was page 7) and the post-treatment
record on Monitor (was page 8); the dry check."""

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dsr_mycodemo import pipeline
from dsr_mycodemo.post_treatment_data import OUTPUT_PATH

APP = Path(__file__).parents[1] / "dsr_mycodemo/app"
START = date(2026, 10, 8)
PLAN = {"batch_label": "M1", "species": "Trametes versicolor", "inoc_date": START, "n_containers": 2,
        "temp_c": 24.0, "substrate": "hemp_hurd", "spawn_pct": 10.0}
D = date(2026, 11, 1)


def _page(name, **state):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(APP / "pages" / name), default_timeout=60)
    s = at.session_state
    s["goal"], s["choice"], s["material_species"], s["temp_c"] = "Materials", "Foam", "Trametes versicolor", 24.0
    s["environment"], s["env_where"] = "Small plastic container (about 1 L)", "Plastic container"
    s["recipe"] = {"main": "hemp_hurd", "substrate": "straw", "spawn_pct": 10.0}
    for k, v in state.items():
        s[k] = v
    at.run()
    assert not at.exception, at.exception
    return at


def _steps(**state):
    """Recipe and actions with the post-treatment steps shown (was page 7)."""
    return _page("2_Recipe_and_actions.py", show_next_steps=True, **state)


def _text(at):
    return " ".join([m.value for m in at.markdown] + [c.value for c in at.caption] + [i.value for i in at.info])


# --- dry check ------------------------------------------------------------------------------------------
def _log(*grams, step=1):
    return [{"date": D + timedelta(days=step * i), "g": g} for i, g in enumerate(grams)]


def test_weight_change_per_day():
    rows = pipeline.weight_changes(_log(200, 180, 171, step=2)[::-1])        # any order in, date order out
    assert [r["g"] for r in rows] == [200, 180, 171]
    assert rows[0]["pct_per_day"] is None
    assert rows[1]["pct_per_day"] == pytest.approx(-5.0) and rows[2]["pct_per_day"] == pytest.approx(-2.5)


def test_stable_weight_is_dry():
    assert pipeline.is_dry(_log(200, 150, 149, 148.5))                        # -0.67 %, -0.34 % per day


def test_still_losing_weight_is_not_dry():
    assert not pipeline.is_dry(_log(200, 180, 170, 160))
    assert not pipeline.is_dry(_log(200, 150, 149, 140))                      # the last change is -6 %
    assert not pipeline.is_dry(_log(200, 199))                                 # one change is not two in a row
    assert not pipeline.is_dry([])


def test_same_day_reading_does_not_count_as_stable():
    log = _log(200, 150, 149) + [{"date": D + timedelta(days=2), "g": 149.0}]
    assert not pipeline.is_dry(log)


# --- method picker reads post_treatment.csv --------------------------------------------------------------------
def test_methods_come_from_post_treatment_csv(tmp_path):
    if not OUTPUT_PATH.exists():
        pytest.skip("post_treatment.csv not built")
    csv = pd.read_csv(OUTPUT_PATH)
    methods = pipeline.post_treatment_methods()
    assert [m["protocol_id"] for m in methods] == csv["protocol_id"].tolist()
    other = tmp_path / "pt.csv"
    csv.iloc[:2].to_csv(other, index=False)
    assert [m["protocol_id"] for m in pipeline.post_treatment_methods(other)] == csv["protocol_id"].tolist()[:2]
    assert pipeline.post_treatment_methods(tmp_path / "missing.csv") == []


def test_method_text_shows_values_or_says_there_are_none():
    by_id = {m["protocol_id"]: m for m in pipeline.post_treatment_methods()}
    if not by_id:
        pytest.skip("post_treatment.csv not built")
    assert pipeline.post_treatment_text(by_id["OVEN-DRY"]) == \
        "40–103 °C (median 70), 10–48 h (median 12). 31 rows from 7 studies."
    assert pipeline.post_treatment_text(by_id["OVEN-BAKE"]) == "100 °C, 6 h. 4 rows from 1 study."
    assert pipeline.post_treatment_text(by_id["COMPACT-50"]) == "No values in our data (4 rows from 1 study)."


def test_steps_method_picker_lists_the_csv_methods():
    at = _steps(batch=PLAN)
    radio = at.radio(key="pt_method")
    assert radio.options == [pipeline.post_treatment_label(m) for m in pipeline.post_treatment_methods()]
    assert "Compact 50% after colonisation" in radio.options
    assert "31 rows from 7 studies" in _text(at)
    radio.set_value("COMPACT-50").run()
    assert "No values in our data" in _text(at) and "density ×1.47" in _text(at)


# --- matched pairs: the notes match the strength table ---------------------------------------------------------
def _pairs(table, pairs, col):
    t = table.set_index("sample_id")
    return len(pairs), float(np.exp(np.mean([np.log(t.at[b, col] / t.at[a, col]) for a, b in pairs])))


def test_matched_pair_notes_match_the_strength_table():
    from dsr_mycodemo.property_data import OUTPUT_PATH as TABLE
    if not TABLE.exists():
        pytest.skip("property_table.csv not built")
    t = pd.read_csv(TABLE)
    ids = set(t["sample_id"])
    d7 = [i for i in ids if i.startswith("d007") and i.endswith("C0")]
    d23 = [i for i in ids if i.startswith("d023")]
    found = {
        "CHITOSAN-2L": _pairs(t, [(i, i[:-1] + "2") for i in d7 if i[:-1] + "2" in ids], "stress_mpa"),
        "CHITOSAN-4L": _pairs(t, [(i, i[:-1] + "4") for i in d7 if i[:-1] + "4" in ids], "stress_mpa"),
        "COMPACT-50": _pairs(t, [(i.replace("-SC", "-SNC").replace("-LC", "-LNC"), i) for i in d23
                                 if "-SC" in i or "-LC" in i], "density_kg_m3"),
        "OVEN-BAKE": _pairs(t, [(i, i[:-1] + "B") for i in d23 if i.endswith("D")], "density_kg_m3"),
    }
    for pid, (n, factor) in found.items():
        _, _, stated, stated_n, _ = pipeline.POST_TREATMENT_PAIRS[pid]
        assert (n, round(factor, 2)) == (stated_n, stated), pid


def test_steps_strength_after_colonisation_and_note_is_text_only():
    at = _steps(batch=PLAN)
    labels = [m.label for m in at.metric if "after colonisation" in m.label]
    if not labels:
        pytest.skip("property_table.csv not available")
    assert labels == ["Stress at 10 % strain (after colonisation)", "Density (after colonisation)"]
    at.radio(key="pt_method").set_value("CHITOSAN-2L").run()
    assert "strength ×0.67" in _text(at) and "8 matched pairs" in _text(at) and "not applied" in _text(at)
    assert "×4" not in _text(at)                                    # pressing while growing belongs to colonisation


def test_steps_start_date_asks_when_nothing_is_typed():
    at = _steps(batch=PLAN)
    assert at.date_input(key="plan_next_start").value is None
    assert any("No 'Fully colonised on' date" in i.value for i in at.info)
    typed = _steps(batch=PLAN, outcomes={"M1-01": {"colonised": D, "mould": False}})
    assert typed.date_input(key="plan_next_start").value == D


def test_steps_materials_residences():
    at = _steps(batch=PLAN)
    labels = [b.label for b in at.button if b.key and b.key.startswith("next_where_")]
    assert labels == ["Oven", "Drying rack or room", "Press"]
    at.button(key="next_where_Oven").click().run()
    assert at.session_state["residences"]["next"] == "Oven"


# --- post-treatment on Monitor (was page 8) ------------------------------------------------------------------
def _monitor(**state):
    return _page("4_Monitor.py", batch=PLAN, residences={"next": "Oven"}, batch_stage="Post-treatment", next_start=D,
                 **state)


def test_monitor_post_treatment_box_has_temperature_and_humidity_only():
    at = _monitor()
    assert [h.value for h in at.subheader][-1] == "Oven"
    keys = {n.key for n in at.number_input}
    assert "mon_temp_Oven_post" in keys and "mon_rh_Oven_post" in keys
    assert not any(k and k.startswith("mon_co2_Oven") for k in keys)


def test_monitor_weight_log_and_dry_message():
    log = _log(200, 150, 149, 148.5)
    at = _monitor(weights={"M1-01": log})
    text = _text(at)
    assert "M1-01 is dry" in " ".join(s.value for s in at.success)
    assert "-25.0 % per day" in text and "Project rule" in text
    at.number_input(key="w_g_M1-01").set_value(140.0).run()
    at.button(key="w_add_M1-01").click().run()
    assert at.session_state["weights"]["M1-01"][-1]["g"] == 140.0


def test_next_step_button_toggles_the_post_treatment_section():
    at = _page("2_Recipe_and_actions.py", batch=PLAN)
    assert at.button(key="show_next_steps_btn").label == "Show post-treatment steps"
    assert not any(r.key == "pt_method" for r in at.radio)
    at.button(key="show_next_steps_btn").click().run()
    assert any(r.key == "pt_method" for r in at.radio)
