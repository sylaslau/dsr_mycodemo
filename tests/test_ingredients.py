"""data/interim/extracted/cn_ingredients.csv is the ingredient table: every substrate.csv component must be one of
its rows, and every row needs a category and a known value_source."""

import pandas as pd
import pytest

from dsr_mycodemo.config import INTERIM_DATA_DIR

EXTRACTED = INTERIM_DATA_DIR / "extracted"
CATEGORIES = {"WOOD_LOG", "WOOD_CHOPPED", "WOOD_CHIP", "WOOD_SHAVING", "WOOD_DUST", "STRAW", "HUSK", "RICH",
              "PROTEIN", "ENERGY", "MINERAL", "FILLER"}
GROUPS = {"BASE", "PROT", "QSUR", "PH", "AIR", "WATER", "MIN"}


@pytest.fixture(scope="module")
def ingredients():
    path = EXTRACTED / "cn_ingredients.csv"
    if not path.exists():
        pytest.skip("no cn_ingredients.csv in data/interim/extracted/")
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def test_ingredient_names_unique(ingredients):
    assert ingredients["ingredient"].is_unique


def test_every_substrate_component_is_an_ingredient(ingredients):
    path = EXTRACTED / "substrate.csv"
    if not path.exists():
        pytest.skip("no substrate.csv")
    sub = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    used = {v for c in ("component_1", "component_2", "component_3") for v in sub[c] if v}
    assert used - set(ingredients["ingredient"]) == set()


def test_every_row_has_a_known_category(ingredients):
    assert set(ingredients["category"]) <= CATEGORIES
    assert (ingredients["category"] != "").all()


def test_value_source_is_own_or_category(ingredients):
    assert set(ingredients["value_source"]) <= {"own", "category"}


def test_wood_type_only_on_wood_rows(ingredients):
    wood = ingredients["category"].str.startswith("WOOD_")
    assert set(ingredients.loc[wood, "wood_type"]) <= {"hard", "soft", ""}
    assert (ingredients.loc[~wood, "wood_type"] == "").all()


def test_groups_are_known(ingredients):
    assert set(ingredients["group_1"]) | set(ingredients["group_2"]) <= GROUPS | {""}


# --- cultivation/ingredients.py: recipe page choices -----------------------------------------------------
from dsr_mycodemo.cultivation import ingredients as ING  # noqa: E402
from dsr_mycodemo.cultivation import recipe as rc  # noqa: E402


def test_mix_cn_sums_weights_and_never_averages_ratios():
    assert ING.mix_cn({"beech_sawdust": 80, "wheat_bran": 20}) == pytest.approx(78.5, abs=0.5)
    mean_of_ratios = 0.8 * 369 + 0.2 * 18
    assert ING.mix_cn({"beech_sawdust": 80, "wheat_bran": 20}) != pytest.approx(mean_of_ratios, abs=5)


def test_minerals_change_weight_only():
    base = ING.mix_cn({"beech_sawdust": 80, "wheat_bran": 20})
    assert ING.mix_cn({"beech_sawdust": 80, "wheat_bran": 20, "gypsum": 1, "chalk": 1}) == pytest.approx(base)
    assert ING.mix_cn({"gypsum": 1}) is None
    assert ING.mix_cn({"unknown thing": 50, "wheat_bran": 10}) == pytest.approx(18, abs=0.5)


@pytest.mark.parametrize("size, minutes", [("under_1l", 60), ("up_to_1kg", 90), ("1_to_3kg", 150)])
def test_autoclave_time_by_size(size, minutes):
    assert ING.autoclave_time(size)[0] == minutes


def test_autoclave_over_3kg_has_no_time_and_says_split():
    minutes, text = ING.autoclave_time("over_3kg")
    assert minutes is None and text == "Split into bags of 3 kg or less, or use cold pasteurisation."


def test_autoclave_size_from_the_vessel():
    assert ING.autoclave_size_key(0.5, 0.4) == "under_1l"
    assert ING.autoclave_size_key(1.0, 0.8) == "up_to_1kg"
    assert ING.autoclave_size_key(5.0, 2.5) == "1_to_3kg"
    assert ING.autoclave_size_key(10.0, 5.0) == "over_3kg"
    assert ING.autoclave_size_key() == "up_to_1kg"


@pytest.mark.parametrize("method, ticked, mineral", [("STER", True, True), ("STEAM", False, True),
                                                     ("COLD", False, False)])
def test_protein_and_quick_energy_ticks_follow_the_method(method, ticked, mineral):
    assert ING.default_ticked("wheat_bran", method, in_guide=True) is ticked     # PROT
    assert ING.default_ticked("corn_meal", method, in_guide=True) is ticked      # QSUR
    assert ING.default_ticked("gypsum", method, in_guide=True) is mineral        # lime soak: main bulk only
    assert ING.default_ticked("wheat_bran", method, in_guide=False) is False


def test_softwood_offered_only_for_oyster_species():
    assert "softwood" in ING.main_options("Pleurotus ostreatus")
    assert "softwood" in ING.main_options("Pleurotus djamor")
    assert "softwood" not in ING.main_options("Lentinula edodes")
    assert "softwood" not in ING.main_options("Trametes versicolor")
    assert "beech_sawdust" in ING.main_options("Lentinula edodes")
    assert "wheat_bran" not in ING.main_options("Pleurotus ostreatus")       # supplements are not main materials


def test_guide_words_map_to_ingredients():
    assert ING.match_guide_words("Hardwood sawdust (oak, maple, beech)") == "beech_sawdust"
    assert ING.match_guide_words("wheat bran") == "wheat_bran"
    assert ING.match_guide_words("gypsum") == "gypsum"
    assert ING.match_guide_words("CaCO3") == "chalk"
    assert ING.match_guide_words("cereal straw") == "wheat_straw"
    assert ING.match_guide_words("Hydrated lime") == "hydrated_lime"
    assert ING.match_guide_words("Hardwood natural logs (oak, beech)") is None
    assert ING.match_guide_words("moon dust") is None


def test_guide_supplements_amounts_and_ticks():
    found, left = ING.guide_supplements("15-20% wheat/rice bran, 1% CaCO3 (chalk, garden lime), 1% gypsum")
    assert found == {"wheat_bran": {"pct": 17.5, "ticked": True}, "rice_bran": {"pct": 17.5, "ticked": False},
                     "chalk": {"pct": 1.0, "ticked": True}, "gypsum": {"pct": 1.0, "ticked": True}}
    assert left == []
    found, _ = ING.guide_supplements("None or 1% CaCO3 (chalk, garden lime)")
    assert found == {"chalk": {"pct": 1.0, "ticked": False}}
    assert ING.guide_supplements(float("nan")) == ({}, [])


def test_parse_supplements_keeps_commas_inside_brackets():
    found, left = rc.parse_supplements("15% wheat bran, 1% CaCO3 (chalk, garden lime)")
    assert [(s["name"], s["pct"]) for s in found] == [("wheat bran", 15.0), ("CaCO3 (chalk, garden lime)", 1.0)]
    assert left == []


def test_recipe_uses_the_chosen_mix():
    mix = {"main_name": "Beech sawdust", "supplements": [{"name": "Gypsum (CaSO4)", "pct": 2.0}]}
    r = rc.recipe("Pleurotus ostreatus", "sawdust", 1.0, 1, mix=mix)
    assert [(i["name"], round(i["kg"], 3)) for i in r["ingredients"]] == [("Beech sawdust", 0.98),
                                                                          ("Gypsum (CaSO4)", 0.02)]
    with pytest.raises(ValueError):
        rc.recipe("Pleurotus ostreatus", "sawdust", 1.0, 1,
                  mix={"main_name": "x", "supplements": [{"name": "y", "pct": 100}]})


def test_autoclave_line_from_the_page2_vessel():
    # glass jar under 1 L -> 60 min; 1 L jar -> by damp weight (up to 1 kg: 90 min)
    assert ING.autoclave_line("Glass Jar", 0.5, 1, 0.25) == (
        60, "Your 0.5 L glass jar, about 0.25 kg damp mix each: 60 min at 121 °C (15 psi).")
    assert ING.autoclave_line("Glass Jar", 1.0, 3, 0.35) == (
        90, "Your 1 L glass jars, about 0.35 kg damp mix each: 90 min at 121 °C (15 psi).")
    assert ING.autoclave_line("Grow bag", 5.0, 2, 2.5)[0] == 150
    minutes, text = ING.autoclave_line("Grow bag", 10.0, 2, 5.0)
    assert minutes is None and text.endswith(ING.OVER_3KG_MESSAGE)
    assert ING.autoclave_line(None, None, 1, 0.5) == (None, "Choose a vessel on Environment.")


def test_grams_switch_to_kg_at_1000():
    assert ING.unit_for(999.9) == ("g", 1.0)
    assert ING.unit_for(1000) == ("kg", 1000.0)
    assert ING.fmt_weight(630.4, ING.unit_for(630.4)) == "630 g"
    assert ING.fmt_weight(1490, ING.unit_for(1490)) == "1.49 kg"


@pytest.mark.parametrize("method", list(ING.METHODS))
def test_steps_follow_the_method(method):
    keys = [k for k, _ in ING.STEPS[method]]
    assert keys == ["recipe", "treat", "spawn"]
    titles = [t for _, t in ING.STEPS[method]]
    if method == "STER":      # mix and fill first, sterilise, then spawn per vessel
        assert "fill vessels" in titles[0] and titles[1] == "Sterilise" and "add spawn" in titles[2]
    else:                     # treat the bulk first, fill vessels only after the spawn goes in
        assert "fill" not in titles[0] and "fill vessels" in titles[2]


def test_amounts_water_and_spawn_per_method():
    ster = ING.amounts(0.2, 65, 3, "STER", 10, handling=1.0)
    steam = ING.amounts(0.2, 65, 3, "STEAM", 10, handling=1.0)
    cold = ING.amounts(0.2, 65, 3, "COLD", 10, handling=1.0)
    water = rc.water_to_add(0.2, 65)
    spawn = rc.spawn_kg(0.2 + water, 10)
    # water row only for STER; spawn never in the sum
    assert ster["water_total"] == pytest.approx(water * 3000) and steam["water_total"] is None
    assert ster["sum"] == pytest.approx((0.2 + water) * 3000)
    assert steam["sum"] == cold["sum"] == pytest.approx(600)
    # per vessel: STER before spawn; STEAM and COLD damp mix + spawn
    assert ster["per_vessel"] == pytest.approx((0.2 + water) * 1000)
    assert steam["per_vessel"] == cold["per_vessel"] == pytest.approx((0.2 + water + spawn) * 1000)
    assert ster["spawn_per_vessel"] == pytest.approx(spawn * 1000)


def test_supplement_rows_in_order_and_empty_rows_left_out():
    rows = ING.supplement_rows()
    assert list(rows)[:4] == ["QSUR", "PROT", "PH", "AIR"]
    assert all(rows.values())
    assert "cottonseed_hulls" in ING.supplement_rows(["cottonseed_hulls"])["OTHER"]
