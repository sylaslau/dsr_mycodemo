"""Build the property table for M3: one row per sample with density and/or stress.

Run from the project root:  python -m dsr_mycodemo.property_data
"""

from pathlib import Path

import pandas as pd

from dsr_mycodemo.config import INTERIM_DATA_DIR, PROCESSED_DATA_DIR

EXTRACTED_DIR = INTERIM_DATA_DIR / "extracted"
OUTPUT_PATH = PROCESSED_DATA_DIR / "materials" / "property_table.csv"

# d005 PFL specimens LF_1/LF_2 sit in the pre-compression sheet but were left out of
# the PFL mean, and their treatment is unknown (flag CF7)
PRE_COMPRESSION_UNKNOWN = {"d005-S-PFL-C-4", "d005-S-PFL-C-5"}

# outcome.measure_id -> property table column
OUTCOME_COLUMNS = {"compressive_stress_10pct": "stress_mpa", "dry_density": "density_kg_m3"}

# ST6 process steps -> the short post_treatment words the table has always used
POST_TREATMENT_TEXT = {
    "OVEN-DRY": "oven_dry", "OVEN-BAKE": "oven_bake", "DRY": "dried", "COMPACT-50": "compact_50pct",
    "CHITOSAN-2L": "chitosan_2_layers", "CHITOSAN-4L": "chitosan_4_layers",
}

# Broad substrate groups, so different labs can share a category
SUBSTRATE_GROUP = {
    "hemp": "hemp",
    "flax": "flax",
    "flax waste": "flax",
    "softwood": "softwood",
    "beech sawdust": "hardwood",
    "birch sanding dust": "hardwood",
    "birch sanding dust + hemp shives": "hardwood",
    "birch sanding dust + birch sawdust": "hardwood",
    "wheat straw": "straw",
    "straw": "straw",
    "wheat straw + hemp shives": "straw",
    "wheat straw + birch sawdust": "straw",
    "arboloco pith": "pith",
    "arboloco pith + kikuyu grass": "pith",
}


def load_tables(folder: Path = EXTRACTED_DIR) -> dict[str, pd.DataFrame]:
    """Read the extracted CSVs that M3 needs."""
    names = ["outcome", "sample", "fermentation", "substrate", "process"]
    return {n: pd.read_csv(folder / f"{n}.csv", encoding="utf-8-sig") for n in names}


def treatment_columns(process: pd.DataFrame) -> pd.DataFrame:
    """One row per fermentation_id: the pressing/coating yes-no columns and the post-treatment text, from process.csv.

    post_treatment is the ST6 steps in step order, joined with "+" (e.g. "compact_50pct+oven_dry").
    """
    p = process.sort_values(["fermentation_id", "step_no"])
    ids = p.groupby("fermentation_id")["protocol_id"]
    out = pd.DataFrame({
        "has_compress": ids.apply(lambda s: s.eq("COMPRESS-20").any()),
        "has_compact": ids.apply(lambda s: s.eq("COMPACT-50").any()),
        "coated": ids.apply(lambda s: s.isin(["CHITOSAN-2L", "CHITOSAN-4L"]).any()),
    })
    post = p[p["stage_id"] == "ST6"]
    out["post_treatment"] = post.groupby("fermentation_id")["protocol_id"].apply(
        lambda s: "+".join(POST_TREATMENT_TEXT[c] for c in s))
    return out.reset_index()


def build_property_table(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Join outcome -> sample -> fermentation, substrate and process steps."""
    o = tables["outcome"]
    o = o[o["measure_id"].isin(OUTCOME_COLUMNS)]
    if o.duplicated(["sample_id", "measure_id"]).any():
        raise ValueError("A sample has more than one strength/density row")
    # one row per sample, as the old wide measurement table had
    m = (o.pivot(index=["dataset_id", "sample_id", "measurement_type"], columns="measure_id", values="value")
         .rename(columns=OUTCOME_COLUMNS).reset_index())
    m.columns.name = None
    if m["sample_id"].duplicated().any():
        raise ValueError("A sample has more than one strength/density row")

    # n_specimens: how many blocks a row stands for (a group mean counts its group)
    s = tables["sample"][["sample_id", "n_specimens", "substrate_id", "fermentation_id"]]
    f = tables["fermentation"][
        ["fermentation_id", "genus", "species", "spawn_pct_wt", "incubation_temp_c", "total_growth_days"]
    ]
    sub = tables["substrate"][["substrate_id", "plant_name", "particle_size_class"]]

    t = m.merge(s, on="sample_id", how="left", validate="one_to_one")
    t = t.merge(f, on="fermentation_id", how="left", validate="many_to_one")
    t = t.merge(sub, on="substrate_id", how="left", validate="many_to_one")
    t = t.merge(treatment_columns(tables["process"]), on="fermentation_id", how="left", validate="many_to_one")

    t["species_name"] = t["genus"] + " " + t["species"]
    # Species is a model input: blocks with no recorded fungus (d006 density blocks, flag HF7) stay out
    t = t[t["species_name"].notna()]
    t["substrate_group"] = t["plant_name"].map(SUBSTRATE_GROUP)
    t["coated"] = t["coated"].fillna(False).astype(bool)
    # 1 = pressed while growing (d005 P samples, 100 -> 80 mm; process step COMPRESS-20), 0 = not, empty = unknown
    t["pre_compressed"] = t["has_compress"].fillna(False).astype(float)
    # 1 = compacted after growth, before drying (d023, process step COMPACT-50, to half thickness).
    # Kept separate: growth after pressing (d005) did not raise density, compaction did.
    t["compacted_after_growth"] = t["has_compact"].fillna(False).astype(float)
    t.loc[t["sample_id"].isin(PRE_COMPRESSION_UNKNOWN), "pre_compressed"] = float("nan")
    cols = [
        "dataset_id", "sample_id", "measurement_type", "n_specimens",
        "species_name", "plant_name", "substrate_group", "particle_size_class",
        "spawn_pct_wt", "incubation_temp_c", "total_growth_days",
        "pre_compressed", "compacted_after_growth", "post_treatment", "coated", "density_kg_m3", "stress_mpa",
    ]
    return t[cols].sort_values(["dataset_id", "sample_id"]).reset_index(drop=True)


def main(output_path: Path = OUTPUT_PATH) -> pd.DataFrame:
    table = build_property_table(load_tables())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(output_path, index=False)
    print(f"Saved {len(table)} rows to {output_path}")
    return table


if __name__ == "__main__":
    main()
