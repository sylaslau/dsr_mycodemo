"""Part B (11-18): the environment section (page 1 since the 5-page flow) switches by mode (Materials adds containers and moulds); one residence per stage."""

from datetime import date
from pathlib import Path

import pytest

from dsr_mycodemo import pipeline
from dsr_mycodemo.app import stage_ui
from dsr_mycodemo.pipeline import Batch

APP = Path(__file__).parents[1] / "dsr_mycodemo/app"
START = date(2026, 10, 8)


def _page(name):
    from streamlit.testing.v1 import AppTest
    return AppTest.from_file(str(APP / name), default_timeout=60)


def _env(goal, choice, **state):
    at = _page("pages/1_Start_a_batch.py")
    at.session_state["goal"], at.session_state["choice"] = goal, choice
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    assert not at.exception
    return at


def _labels(at):
    return [b.label for b in at.button]


# --- page 2 by mode ---------------------------------------------------------------------------
def test_materials_shows_containers_and_moulds():
    at = _env("Materials", "Packaging foam")
    subs = [s.value for s in at.subheader]
    assert subs[subs.index("Residence"):][:3] == ["Residence", "Containers", "Vessels"]
    for name in ("Micro box", "Crate", "Filter bag", "Mould (box)", "Mould (cylinder)", "Grow Bag"):
        assert name in _labels(at), name
    for food_only in ("Glass Jar", "Tupperware", "Bucket"):
        assert food_only not in _labels(at)


def test_food_shows_no_containers():
    at = _env("Food", "Blue Oyster")
    assert "Containers" not in [s.value for s in at.subheader]
    for name in ("Micro box", "Crate", "Filter bag", "Mould (box)"):
        assert name not in _labels(at)
    assert {"Glass Jar", "Tupperware", "Grow Bag", "Bucket"} <= set(_labels(at))


def test_container_click_saves_env_box_and_a_second_click_clears_it():
    at = _env("Materials", "Packaging foam")
    at.button(key="box_Crate").click().run()
    assert at.session_state["env_box"] == "Crate"
    at.button(key="box_Crate").click().run()
    assert at.session_state["env_box"] is None


def test_residence_click_keeps_the_old_keys_and_saves_per_stage():
    at = _env("Food", "Blue Oyster")
    at.button(key="where_Tent or Cabinet").click().run()
    s = at.session_state
    assert s["env_where"] == "Tent or Cabinet" and s["environment"] == "Shelf or grow tent"
    assert s["residences"] == {"colonisation": "Tent or Cabinet"}


def test_old_session_keys_still_load():
    at = _env("Food", "Blue Oyster", env_where="Tent or Cabinet", env_container="Glass Jar",
              env_size={"Tent or Cabinet": 2.0, "Glass Jar": 0.5}, env_amount={"Tent or Cabinet": 3, "Glass Jar": 4},
              environment="Shelf or grow tent")
    assert at.button(key="where_Tent or Cabinet").proto.type == "primary"
    assert at.button(key="cont_Glass Jar").proto.type == "primary"
    assert at.number_input(key="size_Glass Jar").value == 0.5 and at.number_input(key="amount_Glass Jar").value == 4
    assert at.number_input(key="size_Tent or Cabinet").value == 2.0


def test_mould_litres_feed_the_recipe_scale():
    at = _page("pages/3_Recipe_and_timeline.py")
    s = at.session_state
    s["goal"], s["choice"], s["material_species"], s["temp_c"] = "Materials", "Packaging foam", "Trametes versicolor", 22.0
    s["environment"], s["env_where"] = "Small plastic container (about 1 L)", "Plastic container"
    s["env_container"], s["env_size"], s["env_amount"] = "Mould (box)", {"Mould (box)": 2.0}, {"Mould (box)": 3}
    at.run()
    assert not at.exception
    assert at.session_state["plan_size"] == (3, 2.0 * 0.2)


def test_food_vessel_is_ignored_in_materials_mode():
    at = _page("pages/3_Recipe_and_timeline.py")
    s = at.session_state
    s["goal"], s["choice"], s["temp_c"] = "Materials", "Packaging foam", 22.0
    s["environment"], s["env_where"] = "Small plastic container (about 1 L)", "Plastic container"
    s["env_container"], s["env_size"], s["env_amount"] = "Glass Jar", {"Glass Jar": 2.0}, {"Glass Jar": 3}
    at.run()
    assert not at.exception and at.session_state["plan_size"] is None


# --- residences per stage --------------------------------------------------------------------
def test_next_falls_back_to_the_colonisation_residence():
    b = Batch(goal="Food", residences={"colonisation": "Plastic container"})
    assert pipeline.residence(b, "colonisation") == "Plastic container"
    assert pipeline.residence(b, "next") == "Plastic container"
    b.residences["next"] = "Tent or Cabinet"
    assert pipeline.residence(b, "next") == "Tent or Cabinet"
    assert pipeline.residence(b) == "Plastic container"


def test_old_batch_without_residences_still_loads():
    d = Batch(goal="Food", choice="Pleurotus ostreatus", inoc_date=START, env_name="Garage").to_dict()
    d.pop("residences")
    b = Batch.from_dict(d)
    assert b.residences == {}
    assert pipeline.residence(b, "next") == "Garage"
    assert pipeline.residence(Batch(), "next") is None
    with pytest.raises(ValueError):
        pipeline.residence(b, "fruiting")


def test_residences_go_through_the_backup():
    b = Batch(goal="Food", inoc_date=START, residences={"colonisation": "Plastic container", "next": "Room or Chamber"})
    assert Batch.from_dict(b.to_dict()).residences == b.residences


def test_residence_options_by_stage_and_mode():
    assert stage_ui.residence_options("colonisation", materials=True) is stage_ui.RESIDENCES
    assert stage_ui.residence_options("next", materials=False) is stage_ui.RESIDENCES
    assert list(stage_ui.residence_options("next", materials=True)) == ["Oven", "Drying rack or room", "Press"]
    with pytest.raises(ValueError):
        stage_ui.residence_options("fruiting")
