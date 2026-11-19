"""Part A (11-18): Material strength uses the substrate group of the recipe's main ingredient, not always hardwood."""

import pytest

from dsr_mycodemo import pipeline
from dsr_mycodemo.cultivation import ingredients as ING
from dsr_mycodemo.pipeline import Batch, run


def materials(main=None, species=None):
    recipe = {"main": main} if main else None
    return Batch(goal="Materials", choice="Packaging foam", material_species=species, recipe=recipe)


def strength(main=None, species=None):
    out = run(materials(main, species)).outcome
    if out.source != "our model":
        pytest.skip("property_table.csv not available")
    return out


@pytest.mark.parametrize("main, group", [
    ("hemp_hurd", "hemp"), ("hemp_chopped", "hemp"), ("flax_shives", "flax"), ("flax_waste", "flax"),
    ("softwood", "softwood"), ("beech_sawdust", "hardwood"), ("birch_dust", "hardwood"),
    ("hazelnut_branch", "hardwood"), ("wheat_straw", "straw"), ("rice_straw", "straw"),
    ("arboloco_pith", "pith"), ("corncobs", None), ("rice_husk", None), ("not_an_ingredient", None)])
def test_main_ingredient_maps_to_the_strength_group(main, group):
    assert ING.strength_group(main) == group


def test_hemp_gives_a_different_estimate_than_hardwood():
    hemp, hard = strength("hemp_hurd"), strength("beech_sawdust")
    assert (hemp.value["substrate_group"], hard.value["substrate_group"]) == ("hemp", "hardwood")
    assert hemp.value["stress_mpa"] != hard.value["stress_mpa"]
    assert hemp.value["density"] != hard.value["density"]
    assert hemp.value["group_matched"] and hard.value["group_matched"]
    assert "instead" not in hemp.note


@pytest.mark.parametrize("main", ["corncobs", None])
def test_unknown_ingredient_falls_back_to_hardwood_with_a_note(main):
    out = strength(main)
    assert out.value["substrate_group"] == "hardwood" and not out.value["group_matched"]
    assert "no substrate group in the strength data, so hardwood is used instead" in out.note
    assert out.value["stress_mpa"] == strength("beech_sawdust").value["stress_mpa"]


@pytest.mark.parametrize("main, species, n_pair, n_species", [
    ("hemp_hurd", "Trametes versicolor", 30, 110), ("beech_sawdust", "Trametes versicolor", 11, 110),
    ("flax_shives", "Trametes versicolor", 30, 110), ("wheat_straw", "Trametes versicolor", 18, 110),
    ("hemp_hurd", "Ganoderma", 21, 63), ("arboloco_pith", "Ganoderma", 6, 63), ("beech_sawdust", "Ganoderma", 0, 63)])
def test_row_counts_for_species_and_group(main, species, n_pair, n_species):
    out = strength(main, species)
    assert (out.value["n_pair"], out.value["n_rows"], out.value["n_total"]) == (n_pair, n_species, 213)
    assert f"based on {n_pair} rows for this species on {out.value['substrate_group']}" in out.note
    assert ("No row has this species on" in out.note) == (n_pair == 0)


def test_hardwood_count_is_19_of_213():
    _, _, total, pairs = pipeline._strength_model()
    hardwood = sum(n for (_, g), n in pairs.items() if g == "hardwood")
    assert (hardwood, total) == (19, 213)
