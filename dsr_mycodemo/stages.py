"""One stage list for the app: data/interim/extracted/stage.csv (ST1 Culture ... ST6 Post-treatment).

The pages keep their own words for the grower ("Colonising", "Fruiting", ...); each word maps to a stage_id here.
"Contaminated" is a status, not a stage, so it maps to None.
"""

from functools import lru_cache

import pandas as pd

from dsr_mycodemo.config import INTERIM_DATA_DIR

STAGE_PATH = INTERIM_DATA_DIR / "extracted" / "stage.csv"

# user-facing word -> stage_id
WORD_TO_STAGE = {
    "Spawning": "ST4",            # Monitor: the inoculation day starts the block's colonisation
    "Inoculated": "ST4",
    "Colonising": "ST4",
    "Colonisation": "ST4",
    "Ready for induction": "ST4",  # end of colonisation, before fruiting conditions start
    "Fruiting": "ST5",
    "Ready for harvest": "ST5",
    "Harvested": "ST5",
    "Post-treatment": "ST6",
    "Contaminated": None,          # a status, not a stage
}


@lru_cache(maxsize=1)
def stage_table() -> pd.DataFrame:
    """stage.csv as read from disk, one row per stage_id (cached)."""
    return pd.read_csv(STAGE_PATH, encoding="utf-8-sig")


def stage_ids() -> list[str]:
    return stage_table()["stage_id"].tolist()


def stage_name(stage_id: str) -> str:
    """'ST4' -> 'Block (colonisation)'."""
    return stage_table().set_index("stage_id").loc[stage_id, "name"]


def stage_of(word):
    """The stage_id behind an app word, or None for a status ('Contaminated') or an unknown word."""
    return WORD_TO_STAGE.get(word)
