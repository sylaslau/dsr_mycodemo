"""Part D (11-18): post-treatment values per ST6 protocol, summarised from process.csv (no invented numbers)."""

import pandas as pd
import pytest

from dsr_mycodemo import post_treatment_data as ptd


@pytest.fixture(scope="module")
def table():
    return ptd.summarise(ptd.load_tables()).set_index("protocol_id")


def test_one_row_per_st6_protocol(table):
    assert list(table.index) == ["COMPACT-50", "OVEN-DRY", "OVEN-BAKE", "DRY", "CHITOSAN-2L", "CHITOSAN-4L"]
    assert table["n_rows"].sum() == 42


def test_oven_dry_and_bake_values(table):
    od, ob = table.loc["OVEN-DRY"], table.loc["OVEN-BAKE"]
    assert (od["n_rows"], od["n_studies"], od["temp_c_min"], od["temp_c_max"]) == (31, 7, 40, 103)
    assert (od["hours_min"], od["hours_max"]) == (10, 48)
    assert (ob["n_rows"], ob["n_studies"], ob["temp_c_min"], ob["temp_c_max"], ob["hours_min"], ob["hours_max"]) == \
        (4, 1, 100, 100, 6, 6)
    assert od["values"] == "" and ob["values"] == ""


@pytest.mark.parametrize("protocol", ["COMPACT-50", "DRY", "CHITOSAN-2L", "CHITOSAN-4L"])
def test_protocols_without_values_say_so_and_stay_empty(protocol, table):
    row = table.loc[protocol]
    assert row["values"] == ptd.NO_VALUES
    assert row[["temp_c_min", "temp_c_median", "temp_c_max", "hours_min", "hours_median", "hours_max"]].isna().all()
    assert row["n_temp"] == 0 and row["n_hours"] == 0


def test_saved_csv_matches_the_summary(table):
    if not ptd.OUTPUT_PATH.exists():
        pytest.skip("post_treatment.csv not built")
    saved = pd.read_csv(ptd.OUTPUT_PATH, keep_default_na=False, na_values=[""]).set_index("protocol_id")
    saved["values"] = saved["values"].fillna("")
    pd.testing.assert_frame_equal(saved, table, check_dtype=False)
