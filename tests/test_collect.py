"""Tests for sharing a batch with the research database (dsr_mycodemo.collect), with a fake Supabase client."""

import io
import re

import numpy as np
from PIL import Image
import pytest

from dsr_mycodemo import collect


class FakeClient:
    """Records table inserts and storage uploads the way supabase.Client is called."""

    def __init__(self):
        self.inserts, self.uploads = {}, {}
        self.storage = self

    def table(self, name):
        client = self

        class Query:
            def insert(self, rows, returning=None):
                assert returning == "minimal"          # anon has no SELECT, so it must not ask for rows back
                client.inserts.setdefault(name, []).extend(rows)
                return self

            def execute(self):
                return None
        return Query()

    def from_(self, bucket):
        assert bucket == "photos"
        return self

    def upload(self, path, data, options=None):
        self.uploads[path] = data


def jpeg_with_exif(w, h):
    """A noisy photo (hard to compress) carrying EXIF with a 90-degree rotation tag."""
    rng = np.random.default_rng(0)
    im = Image.fromarray(rng.integers(0, 255, (h, w, 3), dtype=np.uint8))
    exif = Image.Exif()
    exif[0x0112] = 6                                    # Orientation: rotate 90 CW
    exif[0x010F] = "PhoneMaker"
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=exif.tobytes(), quality=95)
    return buf.getvalue()


def batch(mould=False):
    return {"purpose": "food", "species": "Pleurotus ostreatus", "substrate": "sawdust",
            "ingredients": [{"name": "hardwood sawdust", "kg": 0.4}, {"name": "wheat bran", "kg": 0.1}],
            "water_pct_wt": 54.0, "spawn_pct_wt": 10.0, "temp_c": 22.0, "rh_pct": 85.0,
            "vessel": "Grow bag", "vessel_litres": 2.0, "fill_weight_g": 1000.0,
            "samples": [{"checks": [{"day": 5, "coverage_pct": 30.0}, {"day": 9, "coverage_pct": 80.0}],
                         "colonised_day": 14, "mould": mould, "flushes": [{"day": 30, "fresh_g": 230.0}],
                         "photos": [{"day": 5, "date": "2026-11-01", "data": jpeg_with_exif(400, 300)},
                                    {"day": 5, "date": "2026-11-01", "data": jpeg_with_exif(400, 300)}]},
                        {"checks": [], "colonised_day": None, "mould": False, "flushes": [], "photos": []}]}


def test_contributor_code():
    code = collect.new_contributor_code()
    assert re.fullmatch(r"u-[a-z0-9]{6}", code)
    assert code != collect.new_contributor_code()


def test_photo_is_shrunk_rotated_jpeg_without_exif():
    out = collect.prepare_photo(jpeg_with_exif(4000, 3000))
    im = Image.open(io.BytesIO(out))
    assert im.format == "JPEG"
    assert max(im.size) <= 1280
    assert im.size == (960, 1280)                     # the EXIF rotation was applied (landscape became portrait)
    assert not im.getexif()
    assert "exif" not in im.info


def test_large_photo_comes_out_under_500_kb():
    assert len(collect.prepare_photo(io.BytesIO(jpeg_with_exif(4000, 3000)))) < 500_000


def test_small_photo_is_not_enlarged():
    im = Image.open(io.BytesIO(collect.prepare_photo(jpeg_with_exif(400, 300))))
    assert im.size == (300, 400)


def test_biological_efficiency_maths():
    # 1000 g wet fill at 60 % water = 400 g dry; 200 g fresh mushrooms = 50 % BE
    assert collect.biological_efficiency_pct(200, 1000, 60) == pytest.approx(50.0)
    with pytest.raises(ValueError):
        collect.biological_efficiency_pct(200, 1000, 100)


def test_nothing_is_sent_without_consent():
    client = FakeClient()
    assert collect.submit_batch(client, batch(), False) is None
    assert collect.submit_batch(client, batch(), None) is None
    assert client.inserts == {} and client.uploads == {}


def test_submit_batch_writes_the_tables():
    client = FakeClient()
    code = collect.submit_batch(client, batch(mould=True), "CC BY 4.0")
    ins = client.inserts
    assert set(ins) == {"dataset", "fermentation", "substrate", "container", "process", "sample", "reading", "outcome",
                        "image", "flag"}
    assert ins["dataset"] == [{"dataset_id": code, "citation": "Mycelly app contribution", "license": "CC BY 4.0",
                               "purpose": "food", "status": "submitted"}]
    assert [s["sample_id"] for s in ins["sample"]] == [f"{code}-S-01", f"{code}-S-02"]
    assert ins["sample"][0]["growth_outcome"] == "colonised_d14_mould"
    assert ins["sample"][1]["growth_outcome"] == "not_colonised_no_mould"
    assert ins["fermentation"][0]["genus"] == "Pleurotus" and ins["fermentation"][0]["species"] == "ostreatus"
    assert ins["substrate"][0]["pct_dry_1"] == 80.0 and ins["substrate"][0]["component_2"] == "wheat bran"
    r = ins["reading"]
    assert [(x["day"], x["measure_id"], x["value"]) for x in r] == [
        (5, "surface_colonised_pct", 30.0), (9, "surface_colonised_pct", 80.0), (14, "surface_colonised_pct", 100)]
    assert {x["stage_id"] for x in r} == {"ST4"} and {x["sample_id"] for x in r} == {f"{code}-S-01"}
    o = ins["outcome"]
    assert len(o) == 1 and o[0]["measure_id"] == "biological_efficiency" and o[0]["day"] == 30
    assert o[0]["value"] == pytest.approx(50.0)                         # 230 g / (1000 g x 46 % dry)
    assert ins["process"] == [{"fermentation_id": f"{code}-FER-1", "step_no": 1, "stage_id": "ST4", "protocol_id": "RUN",
                               "vessel_id": f"{code}-C-1", "day_start": 0, "temp_c": 22.0, "rh_pct": 85.0}]
    assert ins["flag"][0]["key_value"] == f"{code}-S-01" and ins["flag"][0]["flag_code"] == "MOULD"
    paths = [r["file_path"] for r in ins["image"]]
    assert paths == [f"{code}/{code}-S-01/day_5.jpg", f"{code}/{code}-S-01/day_5_2.jpg"]
    assert set(client.uploads) == set(paths)
    allowed = {"dataset_id", "citation", "source_url", "license", "lab", "regime", "purpose", "status", "note"}
    assert set(ins["dataset"][0]) <= allowed                              # no new columns


def test_no_flag_rows_without_mould():
    client = FakeClient()
    collect.submit_batch(client, batch(mould=False), "CC BY 4.0")
    assert "flag" not in client.inserts


def test_rows_only_use_columns_of_the_extracted_csvs():
    """reading / outcome / process rows must fit the CSVs (and so the Supabase tables built from them)."""
    import pandas as pd
    from dsr_mycodemo.config import INTERIM_DATA_DIR
    b = batch()
    b["samples"][0]["checks"][0]["score"] = 2
    rows, _ = collect.build_rows("u-test01", b, "CC BY 4.0")
    assert any(x["measure_id"] == "colonisation_score" for x in rows["reading"])
    for table in ("reading", "outcome", "process"):
        cols = set(pd.read_csv(INTERIM_DATA_DIR / "extracted" / f"{table}.csv", nrows=0).columns)
        for row in rows[table]:
            assert set(row) <= cols, (table, set(row) - cols)
