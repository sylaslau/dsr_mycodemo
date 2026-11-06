"""Every vessel/container/residence link in process.csv and fermentation.csv exists in compartment.csv
with the matching role."""

import pandas as pd
import pytest

from dsr_mycodemo.config import INTERIM_DATA_DIR

EXTRACTED = INTERIM_DATA_DIR / "extracted"
LINKS = {"process": ["vessel_id", "container_id", "residence_id"],
         "fermentation": ["vessel_id", "container_id"]}

pytestmark = pytest.mark.skipif(not (EXTRACTED / "compartment.csv").exists(),
                                reason="extracted data not present (data/ is git-ignored)")


def test_compartment_ids_unique_and_roles_valid():
    c = pd.read_csv(EXTRACTED / "compartment.csv")
    assert c["compartment_id"].is_unique
    assert set(c["role"].dropna()) <= {"vessel", "container", "residence"}


@pytest.mark.parametrize("table", LINKS)
def test_links_exist_with_matching_role(table):
    role = pd.read_csv(EXTRACTED / "compartment.csv").set_index("compartment_id")["role"]
    df = pd.read_csv(EXTRACTED / f"{table}.csv")
    bad = []
    for col in LINKS[table]:
        want = col.removesuffix("_id")
        for cid in df[col].dropna().unique():
            if role.get(cid) != want:
                bad.append(f"{table}.{col}={cid} (role {role.get(cid, 'missing')})")
    assert not bad, bad
