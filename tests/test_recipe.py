"""Tests for the consensus recipe maths (dsr_mycodemo.cultivation.recipe)."""

import pytest

from dsr_mycodemo.cultivation import recipe as rc


def test_species_list_comes_from_the_consensus_table():
    sp = rc.species_list()
    assert len(sp) == 8
    assert sp[0] == {"species": "Pleurotus ostreatus", "common_name": "Pearl Oyster"}


def test_water_assumes_dry_ingredients_hold_ten_percent_water():
    assert rc.water_to_add(1, 60) == pytest.approx(1.25)      # 0.9 kg dry matter / 0.4 = 2.25 kg total
    assert rc.water_to_add(1, 60) != pytest.approx(1.5)       # not "dry matter" maths
    assert rc.water_to_add(2, 62) == pytest.approx(2 * 0.9 / 0.38 - 2)
    assert rc.water_to_add(1, 10) == 0                        # already at the target
    assert rc.water_to_add(0, 60) == 0


def test_water_rejects_impossible_input():
    with pytest.raises(ValueError):
        rc.water_to_add(1, 100)
    with pytest.raises(ValueError):
        rc.water_to_add(-1, 60)


def test_spawn_is_a_share_of_the_total_mix():
    s = rc.spawn_kg(9, 10)
    assert s == pytest.approx(1)                              # 1 of 10 kg total
    assert s / (9 + s) == pytest.approx(0.10)
    assert rc.spawn_kg(5, 0) == 0


def test_spawn_warning_outside_five_to_twenty_percent():
    assert rc.spawn_warnings(10) == []
    assert rc.spawn_warnings(5) == [] and rc.spawn_warnings(20) == []
    assert "outside" in rc.spawn_warnings(3)[0]
    assert "outside" in rc.spawn_warnings(25)[0]


def test_supplements_are_parsed_to_midpoints():
    found, left = rc.parse_supplements("10-20% wheat bran, 1% gypsum")
    assert [(s["name"], s["pct"]) for s in found] == [("wheat bran", 15.0), ("gypsum", 1.0)]
    assert left == []
    found, left = rc.parse_supplements("None or 1% lime")
    assert found == [] and left == ["None or 1% lime"]
    assert rc.parse_supplements(float("nan")) == ([], [])


def test_recipe_for_pearl_oyster_on_sawdust():
    r = rc.recipe("Pleurotus ostreatus", "sawdust", 1.0, 3)
    assert r["ref_id"] == "cb03" and r["moisture_pct"] == 62
    assert r["substrate"] == "Hardwood sawdust"
    assert [i["name"] for i in r["ingredients"]] == ["Hardwood sawdust", "wheat bran", "gypsum"]
    assert sum(i["kg"] for i in r["ingredients"]) == pytest.approx(1.0)
    pc = r["per_container"]
    assert pc["water"] == pytest.approx(0.9 / 0.38 - 1)
    assert pc["damp_substrate"] == pytest.approx(0.9 / 0.38)
    assert pc["spawn"] / pc["total_mix"] == pytest.approx(0.10)
    assert r["totals"]["water"] == pytest.approx(3 * pc["water"]) and r["n"] == 3
    assert r["warnings"] == []


def test_recipe_warns_on_unusual_spawn_and_falls_back_to_sawdust():
    r = rc.recipe("Lentinula edodes", "straw", 1.0, 1, spawn_pct=3)       # no shiitake straw row
    assert r["substrate_code"] == "sawdust" and "no straw row" in r["row_note"]
    assert len(r["warnings"]) == 1


def test_unknown_species_raises():
    with pytest.raises(KeyError):
        rc.recipe("Agaricus bisporus", "sawdust", 1.0)
