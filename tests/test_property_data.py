"""Checks for the M3 property table. Run from the project root:  pytest tests"""

import io
from pathlib import Path

import pandas as pd
import pytest

from dsr_mycodemo.property_data import build_property_table, load_tables


@pytest.fixture(scope="module")
def table() -> pd.DataFrame:
    return build_property_table(load_tables())


def test_one_row_per_sample(table):
    assert table["sample_id"].is_unique


def test_every_row_has_a_target(table):
    assert (table["stress_mpa"].notna() | table["density_kg_m3"].notna()).all()


def test_joins_found_species_and_substrate(table):
    assert table["species_name"].notna().all()
    assert table["substrate_group"].notna().all(), "add new plant names to SUBSTRATE_GROUP"


def test_units_are_plausible(table):
    # Stress at 10% strain in MPa, dry density in kg/m3
    assert table["stress_mpa"].dropna().between(0.0005, 2).all()
    assert table["density_kg_m3"].dropna().between(20, 600).all()


def test_group_means_have_specimen_counts(table):
    means = table[table["measurement_type"] == "mean"]
    assert means["n_specimens"].notna().all()


def test_pre_compression_flag(table):
    pressed = table[table["pre_compressed"] == 1]["sample_id"]
    assert pressed.str.contains("-P(?:HL|FL|FWL)-", regex=True).all()
    assert (table.loc[table["dataset_id"] != "d005", "pre_compressed"] == 0).all()
    compacted = table[table["compacted_after_growth"] == 1]["sample_id"]
    assert compacted.str.contains("^d023-G-..-.C[DB]$", regex=True).all()
    assert len(compacted) == 6


def test_treatments_come_from_process_steps(table):
    coated = table[table["coated"]]
    assert set(coated["post_treatment"]) == {"oven_dry+chitosan_2_layers", "oven_dry+chitosan_4_layers"}
    assert table.loc[table["compacted_after_growth"] == 1, "post_treatment"].str.startswith("compact_50pct+").all()


def test_rebuilt_table_matches_the_11_06_table_value_for_value(table):
    """The switch from measurement/fermentation text to outcome/process must not change a single value."""
    saved = pd.read_csv(Path(__file__).parent / "fixtures" / "property_table_20261106.csv")
    rebuilt = pd.read_csv(io.StringIO(table.to_csv(index=False)))      # through CSV, as main() saves it
    assert list(rebuilt.columns) == list(saved.columns)
    pd.testing.assert_frame_equal(rebuilt.set_index("sample_id").sort_index(),
                                  saved.set_index("sample_id").sort_index())
