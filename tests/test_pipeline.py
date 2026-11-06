"""Tests for the pipeline (dsr_mycodemo.pipeline): one batch record, run(batch), and the steps it calls."""

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from dsr_mycodemo import pipeline
from dsr_mycodemo.growth.consensus_estimate import ModelUnavailable
from dsr_mycodemo.growth.coverage import photo_coverage, photo_quality, quality_message
from dsr_mycodemo.growth.forecast import backup_from_json, backup_to_json, logistic
from dsr_mycodemo.pipeline import Batch, Condition, Photo, run

START = date(2026, 10, 8)
END, MARK = pipeline.ENDPOINT_LABEL, pipeline.MARKER_LABEL


@pytest.fixture(autouse=True)
def fallback_maths(monkeypatch):
    """These tests pin the fallback (ref_2 range + temperature rule, logistic fit); the 2.2/2.5 path is tested in
    tests/test_colonisation_wiring.py."""
    def missing():
        raise ModelUnavailable("test: no 2.2 bundle")
    monkeypatch.setattr(pipeline, "_consensus", missing)


def food(**kw):
    kw.setdefault("temp_c", 24.0)
    return Batch(goal="Food", choice="Pleurotus ostreatus", environment="Grow bag (about 3 kg)", inoc_date=START, **kw)


def materials(**kw):
    kw.setdefault("temp_c", 24.0)
    return Batch(goal="Materials", choice="Foam", environment="Grow bag (about 3 kg)", inoc_date=START, **kw)


def photos(n, k=0.8, t50=6.0, days=(1, 3, 5, 7, 9, 11)):
    return [Photo(day=d, file=f"p{d}.jpg", coverage=float(logistic(d, k, t50))) for d in days[:n]]


def event(result, label):
    return next((a, b) for name, a, b in result.dates.value if name == label)


# --- food and materials ----------------------------------------------------------------------
def test_food_batch_steps_and_dates():
    r = run(food())
    assert r.recipe.value["rec"]["totals"]["as_weighed"] > 0
    assert r.colonisation_estimate.source == "fallback: typical range"
    assert r.outcome.name == "Harvest record" and r.outcome.value is None
    assert [n for n, _, _ in r.dates.value] == ["Inoculation", END, MARK, "Pinning",
                                                   "First harvest"]
    a, b = event(r, END)
    assert (a, b) == (START + timedelta(days=14), START + timedelta(days=22))   # cb03 at its optimum (24 °C)
    assert event(r, MARK) == (a + timedelta(days=2), b + timedelta(days=2))     # project assumption: 90% day + 2
    assert event(r, "First harvest") == (a + timedelta(days=11), b + timedelta(days=11))
    assert not any(n == "Colonised (90%)" for n, _, _ in r.dates.value)
    assert r.fruiting.name == "Fruiting" and r.fruiting.value["first_harvest"] == 9


def test_materials_batch_greys_food_timing_and_keeps_recipe_and_strength():
    r = run(materials())
    for step in (r.colonisation_estimate, r.colonisation_forecast, r.dates, r.warnings, r.harvest_readiness):
        assert step.source == pipeline.MATERIALS_PREVIEW and step.is_preview
        assert step.note == pipeline.MATERIALS_PREVIEW_NOTE
    assert r.dates.value == [] and r.warnings.value == [] and r.fruiting is None
    assert r.recipe.source == "typical range" and r.recipe.value["rec"]["totals"]["as_weighed"] > 0
    assert r.mould_check.source == "preview"
    assert r.outcome.name == "Material strength"
    assert r.outcome.source in ("our model", "preview")        # preview only if the model data is missing here
    if r.outcome.source == "our model":
        assert r.outcome.value["stress_mpa"] > 0
        assert pipeline.STRENGTH_LABEL in r.outcome.note


def test_materials_offers_trametes_and_ganoderma_only():
    assert pipeline.MATERIAL_SPECIES == ["Trametes versicolor", "Ganoderma"]
    assert set(pipeline.MATERIAL_SPECIES_DATA.values()) == set(pipeline.MATERIAL_SPECIES)
    assert pipeline.material_species(materials()) == "Trametes versicolor"        # unset = the first
    assert pipeline.material_species(materials(material_species="Pleurotus ostreatus")) == "Trametes versicolor"
    assert pipeline.species_row(materials()) is None and pipeline.baseline_row(materials()) is None
    tv = run(materials()).recipe
    gan = run(materials(material_species="Ganoderma")).recipe
    assert "Pleurotus ostreatus row is used as a generic baseline" in tv.note
    assert gan.value["rec"]["row_note"].startswith(pipeline.baseline_guide.row("Ganoderma lucidum", "sawdust")[0]["ref_id"])


def test_material_strength_uses_the_chosen_species():
    tv, gan = (run(materials(material_species=s)).outcome for s in pipeline.MATERIAL_SPECIES)
    if tv.source != "our model":
        pytest.skip("property_table.csv not available")
    assert (tv.value["species"], gan.value["species"]) == ("Trametes versicolor", "Ganoderma")
    assert tv.value["stress_mpa"] != gan.value["stress_mpa"]
    assert tv.value["n_total"] == 213
    assert (tv.value["n_rows"], gan.value["n_rows"]) == (110, 63)      # Ganoderma = sessile 39 + lingzhi 18 + lucidum 6
    assert "based on 63 rows for this species, out of 213" in gan.note


def test_materials_hide_the_spawn_warning_food_keeps_it():
    assert run(materials(recipe={"spawn_pct": 3})).recipe.value["rec"]["warnings"] == []
    assert run(materials(recipe={"spawn_pct": 3})).warnings.value == []
    assert any("Spawn at 3%" in w for w in run(food(recipe={"spawn_pct": 3})).warnings.value)


def test_food_results_do_not_depend_on_the_materials_switch(monkeypatch):
    b = food(photos=photos(3), conditions=[Condition(START + timedelta(days=2), 22.0, 60.0)])
    limited = repr(run(b))
    monkeypatch.setattr(pipeline, "MATERIALS_MODE", "off")
    assert repr(run(b)) == limited
    assert pipeline.MATERIALS_PREVIEW not in limited


def test_materials_mode_off_and_bad_values(monkeypatch):
    monkeypatch.setattr(pipeline, "MATERIALS_MODE", "off")
    r = run(materials())
    assert r.outcome.source == "preview" and r.outcome.value is None
    assert r.colonisation_estimate.source == pipeline.MATERIALS_PREVIEW
    monkeypatch.setattr(pipeline, "MATERIALS_MODE", "maybe")
    with pytest.raises(ValueError):
        pipeline.materials_mode()


def test_recipe_comes_from_the_consensus_row():
    v = run(food()).recipe.value
    rec = v["rec"]
    assert rec["ref_id"] == "cb03" and v["moisture"] == 62 and v["spawn_pct"] == 10
    assert rec["per_container"]["water"] == pytest.approx(0.9 * rec["per_container"]["as_weighed"] / 0.38
                                                          - rec["per_container"]["as_weighed"])
    assert v["spawn_kg"] / rec["per_container"]["total_mix"] == pytest.approx(0.10)
    bad = run(food(recipe={"spawn_pct": 3}))
    assert any("Spawn at 3%" in w for w in bad.warnings.value)


def test_species_rows_and_legacy_choices_use_consensus_names():
    oyster = pipeline.species_row(food())
    assert oyster == {"species": "Pleurotus ostreatus", "common_name": "Pearl Oyster"}
    assert pipeline.species_row(materials()) is None          # materials have no consensus colonisation row
    old = {**food().to_dict(), "choice": "Blue Oyster"}
    assert Batch.from_dict(old).choice == "Pleurotus ostreatus"
    old["choice"] = "King Oyster"
    assert Batch.from_dict(old).choice == "Pleurotus eryngii"
    assert pipeline.choice_label(food()) == "Pearl Oyster"


def test_blue_oyster_uses_the_sawdust_row_of_the_consensus_guide():
    est = run(food()).colonisation_estimate
    assert est.value["days"] == (14, 22) and est.value["typical"] == 18 and est.value["factor"] == 1.0
    assert est.value["row"].startswith("cb03") and "sawdust" in est.value["row"] and "cb03" in est.note


def test_shiitake_gets_no_temperature_adjustment():
    b = Batch(goal="Food", choice="Lentinula edodes", environment="Grow bag (about 3 kg)", temp_c=15.0, inoc_date=START)
    est = pipeline.colonisation_estimate(b)
    assert est.value["factor"] == 1.0 and "No temperature adjustment" in est.note
    assert est.value["row"].startswith("cb13")
    assert run(b).fruiting.value is not None


def test_fruiting_step_is_food_only_and_flags_inferred():
    assert run(materials()).fruiting is None
    fr = run(food()).fruiting
    assert fr.source == "typical range" and fr.value["inferred"] == (
        fr.value["induction_evidence_status"] == "inferred_from_existing_columns")


def test_custom_species_is_a_preview():
    r = run(Batch(goal="Food", choice="Custom", custom_name="X", environment="Grow bag (about 3 kg)", temp_c=24.0,
                  inoc_date=START))
    assert r.colonisation_estimate.is_preview and r.colonisation_estimate.note
    assert r.dates.value == [] and r.dates.note and r.fruiting.is_preview
    assert r.colonisation_forecast.note


# --- photos: 0, 2, 4 -------------------------------------------------------------------------
def test_zero_photos_uses_the_estimate():
    fc = run(food()).colonisation_forecast
    assert fc.value["method"] == "estimate" and fc.value["n_photos"] == 0
    assert fc.source == "fallback: typical range"


def test_two_photos_nudge_the_estimate():
    base = run(food()).colonisation_forecast.value["day90"]
    fast = run(food(photos=photos(2, t50=3.0))).colonisation_forecast
    slow = run(food(photos=photos(2, t50=12.0))).colonisation_forecast
    assert fast.value["method"] == slow.value["method"] == "nudged"
    assert fast.source == "fallback: photo curve" and "Fallback used" in fast.note
    assert fast.value["day90"] < base < slow.value["day90"]
    assert slow.value["day90"] <= base * pipeline.MAX_NUDGE + 1e-9          # capped at 30 %
    assert run(food(photos=photos(2, t50=3.0))).warnings.value             # "only 2 photos" warning


def test_four_photos_forecast_takes_over():
    r = run(food(photos=photos(4)))
    fc = r.colonisation_forecast
    assert fc.value["method"] == "curve fit" and fc.source == "fallback: photo curve" and fc.value["n_photos"] == 4
    assert fc.value["day90"] == pytest.approx(6 + np.log(9) / 0.8, abs=0.5)   # logistic(k=0.8, t50=6) hits 90 % there
    a, b = event(r, END)
    assert a == b == START + timedelta(days=round(fc.value["day90"]))


def test_forecast_takes_over_exactly_at_three():
    assert run(food(photos=photos(2))).colonisation_forecast.value["method"] == "nudged"
    assert run(food(photos=photos(3))).colonisation_forecast.value["method"] == "curve fit"


def test_unfittable_photos_fall_back_to_the_estimate_and_say_so():
    flat = [Photo(day=d, file=f"f{d}", coverage=0.0) for d in (1, 3, 5)]
    fc = run(food(photos=flat)).colonisation_forecast
    assert fc.value["method"] == "estimate" and "step below" in fc.note


# --- temperature ----------------------------------------------------------------------------
def test_temperature_changes_the_estimate_and_the_dates():
    warm, cool, cold = (run(food(temp_c=t)) for t in (25.0, 18.0, 13.0))
    assert warm.colonisation_estimate.value["days"][0] < cool.colonisation_estimate.value["days"][0] \
        < cold.colonisation_estimate.value["days"][0]
    assert event(warm, END)[1] < event(cold, END)[1]


def test_temperature_factor_shape():
    opt = 24
    assert pipeline.temperature_factor(opt, opt) == (1.0, True)
    assert pipeline.temperature_factor(opt - 5, opt)[0] < 1.0
    f, inside = pipeline.temperature_factor(5.0, opt)
    assert f == pipeline.RATE_FLOOR and not inside


def test_no_temperature_yet_gives_the_typical_range():
    est = run(food(temp_c=None)).colonisation_estimate
    assert est.value["days"] == (14, 22) and est.value["factor"] == 1.0


def test_parse_temp_moved_from_the_notebook():
    assert pipeline.parse_temp("21-27°C (70-80°F); optimum 23-25°C") == (21, 24, 27)
    assert pipeline.parse_temp("24°C (75°F); range 21-27°C (70-80°F)") == (21, 24, 27)


def test_card_days_to_next_stage_is_a_range_that_grows_when_it_is_colder():
    b = food()
    warm = pipeline.days_to_next_stage(b, 0.3, 25.0).value
    cold = pipeline.days_to_next_stage(b, 0.3, 16.0).value
    assert 0 < warm[0] < warm[1] and cold[0] > warm[0]
    assert pipeline.days_to_next_stage(b, 0.95, 24.0).value == (0.0, 0.0)


# --- humidity and temperature warnings --------------------------------------------------------
def test_humidity_out_of_range_warns_but_dates_do_not_move():
    plain = run(food(photos=photos(2)))
    humid = run(food(photos=photos(2), conditions=[Condition(START + timedelta(days=2), 22.0, 99.0)]))
    dry = run(food(photos=photos(2), conditions=[Condition(START + timedelta(days=2), 24.0, 40.0)]))
    assert any("Humidity" in w for w in humid.warnings.value) and any("Humidity" in w for w in dry.warnings.value)
    assert not any("Humidity" in w for w in plain.warnings.value)
    assert humid.dates.value == plain.dates.value == dry.dates.value
    assert humid.colonisation_forecast.value == plain.colonisation_forecast.value


def test_logged_temperature_out_of_range_warns():
    r = run(food(conditions=[Condition(START, 38.0, 90.0)]))
    assert any("Temperature 38" in w for w in r.warnings.value)
    assert not any("Humidity" in w for w in r.warnings.value)


def test_recipe_warnings_are_included():
    r = run(food())
    for w in r.recipe.value["rec"]["warnings"]:
        assert w in r.warnings.value


# --- preview steps ---------------------------------------------------------------------------
def test_harvest_readiness_and_mould_check_are_previews_with_fixed_shapes():
    r = run(food(fruiting_photos=["a.jpg", "b.jpg"]))
    assert r.harvest_readiness.is_preview and r.harvest_readiness.source == "preview"
    assert r.harvest_readiness.value == {"label": None, "score": None, "n_photos": 2}
    assert r.mould_check.is_preview and r.mould_check.value == {"mould": None, "n_photos": 0}
    assert run(materials()).mould_check.is_preview


def test_every_step_has_a_valid_source_and_a_note():
    r = run(food(photos=photos(4)))
    for step in (r.recipe, r.colonisation_estimate, r.colonisation_forecast, r.dates, r.harvest_readiness,
                 r.warnings, r.mould_check, r.outcome):
        assert step.source in pipeline.SOURCES and step.note


# --- batch record and backup ----------------------------------------------------------------
def test_batch_round_trips_through_the_json_backup():
    b = food(photos=photos(3), conditions=[Condition(START, 23.0, 88.0)],
             stages=[pipeline.StageEntry("Colonising", START, "ok")], recipe={"substrate": "sawdust", "spawn_pct": 10})
    payload = {"dataset": "ref", "dish": "d", "batch": {"inoc_date": START}, "dish_fields": {}, "stage_log": {},
               "photos": [], "harvest": {}, "dry_g": {}, "losses": {}, "costs": {}, "pipeline": b.to_dict()}
    back = backup_from_json(backup_to_json(payload))
    assert Batch.from_dict(back["pipeline"]) == b
    del payload["pipeline"]                                           # an older backup still restores
    assert "pipeline" not in backup_from_json(backup_to_json(payload))


# --- per-photo card (Photo coverage method, quality check) ---------------------------------------
def save(tmp_path, name, array):
    p = tmp_path / name
    Image.fromarray(np.asarray(array, np.uint8)).save(p)
    return p


def textured(rng, h=300, w=300, base=(120, 90, 60)):
    return np.clip(np.array(base) + rng.normal(0, 25, (h, w, 3)), 0, 255)


def test_hsv_is_used_when_the_result_is_not_too_pale(tmp_path):
    rng = np.random.default_rng(0)
    img = textured(rng)
    img[100:200, 100:200] = (235, 235, 230)                           # a white patch: about 11 % of the frame
    out = photo_coverage(save(tmp_path, "a.png", img))
    assert out["method"] == "HSV threshold" and not out["too_pale"] and 0.05 < out["coverage"] < 0.25


def test_too_pale_photo_falls_back_to_kmeans(tmp_path):
    rng = np.random.default_rng(1)
    img = np.clip(np.full((300, 300, 3), 235.0) + rng.normal(0, 3, (300, 300, 3)), 0, 255)
    img[:, :150] -= 40                                                # darker half: pale substrate; right half: mycelium
    out = photo_coverage(save(tmp_path, "pale.png", np.clip(img, 0, 255)))
    assert out["too_pale"] and out["method"] == "K-means (Lab colour)"
    assert 0.3 < out["coverage"] < 0.7


def test_too_pale_without_a_split_says_so(tmp_path):
    img = np.full((200, 200, 3), 240)
    out = photo_coverage(save(tmp_path, "flat.png", img))
    assert out["too_pale"] and "found no split" in out["method"]


def test_quality_check_names_the_actual_reason(tmp_path):
    rng = np.random.default_rng(2)
    sharp = save(tmp_path, "sharp.png", textured(rng))
    assert photo_quality(sharp)["ok"] and quality_message(photo_quality(sharp)) == ""
    blur = Image.fromarray(textured(rng).astype(np.uint8)).resize((20, 20)).resize((300, 300))
    blur.save(tmp_path / "blur.png")
    q = photo_quality(tmp_path / "blur.png")
    assert q["reasons"] == ["blurry"]
    assert quality_message(q) == "This photo is blurry. Try taking another one."
    dark = photo_quality(save(tmp_path, "dark.png", textured(rng, base=(15, 15, 15))))
    assert dark["reasons"] == ["too dark"]
    glare = textured(rng)
    glare[:120] = 255
    q = photo_quality(save(tmp_path, "glare.png", glare))
    assert "too bright (glare)" in q["reasons"]
    assert "glare" in quality_message(q)


# --- environments and the next stage ------------------------------------------------------------
def test_environment_validates_size_and_measured_by():
    pipeline.Environment("Shelf", "Shelf", 22.0, 85.0, "Thermometer")
    with pytest.raises(ValueError):
        pipeline.Environment("x", size="Castle")
    with pytest.raises(ValueError):
        pipeline.Environment("x", measured_by="Vibes")


def test_environment_temperature_moves_the_colonisation_estimate():
    cold, warm = pipeline.Environment("Cellar", temp_c=15.0), pipeline.Environment("Kitchen", temp_c=25.0)
    d_cold = run(food(temp_c=cold.temp_c, env_name="Cellar")).colonisation_estimate.value["days"]
    d_warm = run(food(temp_c=warm.temp_c, env_name="Kitchen")).colonisation_estimate.value["days"]
    assert d_cold[0] > d_warm[0]


def test_next_stage_after_colonisation_food_and_materials():
    assert pipeline.next_stage("Food", "Colonising") == "Fruiting"
    assert pipeline.next_stage("Materials", "Colonisation") == "Post-treatment"
    assert pipeline.next_stage("Food", "Fruiting") is None
    assert pipeline.next_stage("Materials", "Post-treatment") is None
    assert pipeline.next_stage("Food", "Contaminated") is None
    assert pipeline.next_stage("Food", None) is None


def test_environment_round_trips_through_the_json_backup():
    env = pipeline.Environment("Garage", "Tent", 19.5, None, "Sensor device")
    b = food(temp_c=env.temp_c, env_name="Garage")
    log = {"dataset": "ref", "dish": "d005", "batch": {"inoc_date": START, "environment": "Garage"},
           "dish_fields": {}, "stage_log": {}, "photos": [], "harvest": {}, "dry_g": {}, "losses": {}, "costs": {},
           "pipeline": b.to_dict(), "environments": {"Garage": env.to_dict()}}
    back = backup_from_json(backup_to_json(log))
    assert pipeline.Environment.from_dict(back["environments"]["Garage"]) == env
    assert Batch.from_dict(back["pipeline"]).env_name == "Garage"


def test_old_backup_without_environments_still_restores():
    log = {"dataset": "ref", "dish": "d005", "batch": {"inoc_date": START}, "dish_fields": {}, "stage_log": {},
           "photos": [], "harvest": {}, "dry_g": {}, "losses": {}, "costs": {}}
    assert "environments" not in backup_from_json(backup_to_json(log))
    assert Batch.from_dict({**food().to_dict(), "env_name": None}).env_name is None


def test_monitor_page_environment_boxes_stages_and_sample_photo():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(Path(__file__).parents[1] / "dsr_mycodemo/app/pages/4_Monitor.py"), default_timeout=60)
    at.session_state["goal"], at.session_state["choice"] = "Food", "Blue Oyster"
    at.session_state["env_where"], at.session_state["env_size"] = "Tent", {"Tent": 1.0}
    at.session_state["batch"] = {"batch_label": "B1", "species": "Pleurotus ostreatus", "inoc_date": START,
                                 "n_containers": 2, "temp_c": 24.0, "substrate": "sawdust", "spawn_pct": 10.0}
    at.run()
    assert not at.exception
    assert [s.value for s in at.subheader] == ["Tent"]
    assert at.selectbox(key="sample_Tent").options == ["B1-01", "B1-02"]
    assert [b.label for b in at.button if b.label in ("Spawning", "Ready for harvest")] == ["Spawning", "Ready for harvest"]
    assert any(b.label == "Save" for b in at.button)



def _page(name):
    from streamlit.testing.v1 import AppTest
    return AppTest.from_file(str(Path(__file__).parents[1] / "dsr_mycodemo/app" / name), default_timeout=60)


def test_recipe_page_materials_shows_previews_and_strength():
    at = _page("pages/3_Recipe_and_timeline.py")
    at.session_state["goal"], at.session_state["choice"] = "Materials", "Packaging foam"
    at.session_state["material_species"] = "Ganoderma"
    at.session_state["environment"], at.session_state["temp_c"] = "Grow bag (about 3 kg)", 22.0
    at.run()
    assert not at.exception
    html_ = " ".join(m.value for m in at.markdown)
    assert html_.count(pipeline.MATERIALS_PREVIEW_NOTE) >= 5    # estimate, forecast, timeline, Warnings, Harvest readiness
    assert not at.warning                                         # no food rules (spawn, temperature)
    if any(m.label == "Density" for m in at.metric):
        assert pipeline.STRENGTH_LABEL in html_


def test_start_page_materials_off_greys_the_things(monkeypatch):
    monkeypatch.setattr(pipeline, "MATERIALS_MODE", "off")
    at = _page("pages/1_Start_a_batch.py")
    at.run()
    assert not at.exception
    assert all(b.disabled for b in at.button if b.key.startswith("thing_"))
    assert not any(b.disabled for b in at.button if b.key.startswith("food_"))


@pytest.mark.parametrize("goal,choice", [("Food", "Blue Oyster"), ("Materials", "Packaging foam")])
def test_environment_page_shows_monotub_and_keeps_saved_value(goal, choice):
    at = _page("pages/2_Environment.py")
    at.session_state["goal"], at.session_state["choice"] = goal, choice
    at.session_state["env_where"] = "Plastic container"          # value saved by older batches
    at.run()
    assert not at.exception
    labels = [b.label for b in at.button]
    assert "Monotub" in labels and "Plastic container" not in labels
    assert "Plastic container with ventilation holes" in [c.value for c in at.caption]
    assert at.button(key="where_Plastic container").label == "Monotub"
