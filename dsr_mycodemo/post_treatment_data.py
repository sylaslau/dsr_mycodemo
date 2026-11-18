"""Build the post-treatment table for page 7 (Materials): one row per ST6 protocol with the study values.

Summarises the ST6 (post-treatment) rows of process.csv per protocol: rows, studies (sample.dataset_id via
fermentation_id), temperature and hours (min / median / max over the rows that state them). Protocols without a
temperature or time say so; no value is ever filled in.

Run from the project root:  python -m dsr_mycodemo.post_treatment_data
"""

from pathlib import Path

import pandas as pd

from dsr_mycodemo.config import INTERIM_DATA_DIR, PROCESSED_DATA_DIR

EXTRACTED_DIR = INTERIM_DATA_DIR / "extracted"
OUTPUT_PATH = PROCESSED_DATA_DIR / "materials" / "post_treatment.csv"
POST_TREATMENT_STAGE = "ST6"
NO_VALUES = "no values in our data"
COLUMNS = ["protocol_id", "name", "n_rows", "n_studies", "studies", "n_temp", "temp_c_min", "temp_c_median",
           "temp_c_max", "n_hours", "hours_min", "hours_median", "hours_max", "values"]


def load_tables(folder: Path = EXTRACTED_DIR) -> dict[str, pd.DataFrame]:
    """Read the extracted CSVs the summary needs."""
    return {n: pd.read_csv(folder / f"{n}.csv", encoding="utf-8-sig") for n in ("process", "protocol", "sample")}


def _hours(rows: pd.DataFrame) -> pd.Series:
    """duration_h, or duration_days x 24 when only days are given."""
    return rows["duration_h"].fillna(rows["duration_days"] * 24)


def summarise(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """One row per ST6 protocol of protocol.csv (in its order), with the values of its process rows."""
    protocols = tables["protocol"]
    protocols = protocols[protocols["stage_id"] == POST_TREATMENT_STAGE]
    p = tables["process"]
    p = p[p["stage_id"] == POST_TREATMENT_STAGE].copy()
    studies = tables["sample"][["fermentation_id", "dataset_id"]].drop_duplicates()
    if studies["fermentation_id"].duplicated().any():
        raise ValueError("A fermentation belongs to more than one study")
    p = p.merge(studies, on="fermentation_id", how="left", validate="many_to_one")
    p["hours"] = _hours(p)
    out = []
    for _, proto in protocols.iterrows():
        rows = p[p["protocol_id"] == proto["protocol_id"]]
        temp, hours = rows["temp_c"].dropna(), rows["hours"].dropna()
        has_values = len(temp) or len(hours)
        out.append({
            "protocol_id": proto["protocol_id"], "name": proto["name"], "n_rows": len(rows),
            "n_studies": rows["dataset_id"].nunique(), "studies": " ".join(sorted(rows["dataset_id"].dropna().unique())),
            "n_temp": len(temp), "temp_c_min": temp.min(), "temp_c_median": temp.median(), "temp_c_max": temp.max(),
            "n_hours": len(hours), "hours_min": hours.min(), "hours_median": hours.median(), "hours_max": hours.max(),
            "values": "" if has_values else NO_VALUES,
        })
    return pd.DataFrame(out, columns=COLUMNS)


def main(output_path: Path = OUTPUT_PATH) -> pd.DataFrame:
    table = summarise(load_tables())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(output_path, index=False)
    print(f"Saved {len(table)} rows to {output_path}")
    return table


if __name__ == "__main__":
    main()
