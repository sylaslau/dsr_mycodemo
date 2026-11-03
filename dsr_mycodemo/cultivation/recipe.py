"""Recipe maths from the consensus table (data/processed/food/cultivation_baseline.csv and cultivation_guide_text.csv).

- Substrate and supplementation: the guide's text for the species and substrate row.
- Water: brings the mix to the row's substrate_moisture_pct, assuming the dry ingredients already hold
  START_MOISTURE_PCT (10 %) water as weighed. This is a project assumption, not a measurement.
- Spawn: a share of the TOTAL mix (substrate + water + spawn), default 10 %; outside 5-20 % only warns.
No yield estimate is made here: the user records their own harvest in Monitor.
"""

import re

import pandas as pd

from dsr_mycodemo.cultivation import baseline_guide

START_MOISTURE_PCT = 10.0
DEFAULT_SPAWN_PCT = 10.0
SPAWN_WARN_RANGE = (5.0, 20.0)
DEFAULT_SUBSTRATE = baseline_guide.FALLBACK_SUBSTRATE

_SUPPLEMENT = re.compile(r"^\s*(\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?\s*%\s+(.+?)\s*$")


def species_list() -> list[dict[str, str]]:
    """Species of the consensus table as [{'species': latin name, 'common_name': ...}], table order."""
    species = baseline_guide.load()[["species", "common_name"]].drop_duplicates()
    return species.to_dict("records")


def water_to_add(as_weighed_kg: float, moisture_pct: float, start_moisture_pct: float = START_MOISTURE_PCT) -> float:
    """kg of water to add so the damp substrate holds moisture_pct water, when the as-weighed dry ingredients
    already hold start_moisture_pct. Example: 1 kg at 60 % -> 1.25 kg (0.9 kg dry matter / 0.4 = 2.25 kg total)."""
    if as_weighed_kg < 0:
        raise ValueError("as_weighed_kg must be 0 or more")
    if not 0 <= start_moisture_pct < 100 or not 0 <= moisture_pct < 100:
        raise ValueError("moisture percentages must be from 0 to below 100")
    dry_matter = as_weighed_kg * (1 - start_moisture_pct / 100)
    return max(dry_matter / (1 - moisture_pct / 100) - as_weighed_kg, 0.0)


def spawn_kg(substrate_kg: float, spawn_pct: float) -> float:
    """kg of spawn so that spawn is spawn_pct % of the total mix: spawn / (substrate + spawn)."""
    if not 0 <= spawn_pct < 100:
        raise ValueError("spawn_pct must be from 0 to below 100")
    return substrate_kg * spawn_pct / (100 - spawn_pct)


def spawn_warnings(spawn_pct: float) -> list[str]:
    low, high = SPAWN_WARN_RANGE
    if spawn_pct < low or spawn_pct > high:
        return [f"Spawn at {spawn_pct:g}% of the mix is outside the usual {low:g}-{high:g}%: "
                "colonisation may be slower (too little) or the spawn wasted (too much)."]
    return []


def parse_supplements(text) -> tuple[list[dict], list[str]]:
    """Split the guide's supplementation text into [{'name', 'pct'}] (midpoint of a range, as % of the as-weighed
    dry ingredients) and the leftover pieces that carry no plain percentage (shown as text only)."""
    if not isinstance(text, str) or not text.strip():
        return [], []
    found, left = [], []
    for part in text.split(","):
        m = _SUPPLEMENT.match(part)
        if m and " or " not in m.group(3):
            low = float(m.group(1))
            high = float(m.group(2)) if m.group(2) else low
            found.append({"name": m.group(3), "pct": (low + high) / 2, "range": (low, high)})
        elif part.strip():
            left.append(part.strip())
    return found, left


def recipe(species: str, substrate_code: str, as_weighed_kg: float, n_containers: int = 1,
           spawn_pct: float = DEFAULT_SPAWN_PCT) -> dict:
    """The recipe for one species on one substrate (falls back like baseline_guide.row).

    as_weighed_kg is the dry ingredients per container as weighed. Returns per-container and total amounts."""
    row, row_note = baseline_guide.row(species, substrate_code)
    text = baseline_guide.load_text()
    text = text[text["ref_id"] == row["ref_id"]].iloc[0]
    moisture = float(row["substrate_moisture_pct"])
    supplements, text_only = parse_supplements(text["substrate_supplementation"])
    supplement_pct = sum(s["pct"] for s in supplements)
    ingredients = [{"name": str(text["substrate"]), "kg": as_weighed_kg * (1 - supplement_pct / 100)}]
    ingredients += [{"name": s["name"], "kg": as_weighed_kg * s["pct"] / 100} for s in supplements]
    water = water_to_add(as_weighed_kg, moisture)
    damp = as_weighed_kg + water
    spawn = spawn_kg(damp, spawn_pct)
    per_container = {"as_weighed": as_weighed_kg, "water": water, "damp_substrate": damp, "spawn": spawn,
                     "total_mix": damp + spawn}
    n = max(int(n_containers), 1)
    return {"ref_id": row["ref_id"], "row_note": row_note, "species": species, "substrate_code": row["substrate_code"],
            "substrate": str(text["substrate"]),
            "supplementation": None if pd.isna(text["substrate_supplementation"]) else text["substrate_supplementation"],
            "supplements": supplements, "supplements_text_only": text_only,
            "ingredients": ingredients, "moisture_pct": moisture, "spawn_pct": spawn_pct,
            "per_container": per_container, "totals": {k: v * n for k, v in per_container.items()},
            "n": n, "warnings": spawn_warnings(spawn_pct)}
