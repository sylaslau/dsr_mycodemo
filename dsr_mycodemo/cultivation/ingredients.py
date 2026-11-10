"""Ingredient table (data/interim/extracted/cn_ingredients.csv) and the recipe page's choices.

- Main material (bulk): one ingredient of a WOOD_*, STRAW or HUSK category.
- Supplements: grouped by function (GROUPS); each ingredient sits under its group_1, group_2 is shown as a tag.
- Treatment method (METHODS) and the autoclave time by jar or bag size (AUTOCLAVE_SIZES).
- mix_cn: C:N of the dry mix = sum(weight x C%) / sum(weight x N%); ratios are never averaged.
Values are general consensus, not measurements.
"""

import re
from functools import lru_cache

import pandas as pd

from dsr_mycodemo.config import INTERIM_DATA_DIR

INGREDIENTS_CSV = INTERIM_DATA_DIR / "extracted" / "cn_ingredients.csv"

# function code -> (name, one-line purpose)
GROUPS = {
    "PROT": ("Protein boost", "Adds nitrogen so the mycelium can build enzymes faster."),
    "QSUR": ("Quick energy", "Simple starch and sugar for a quick start (but also feeds moulds)."),
    "PH": ("pH balance", "Stops the mix turning sour as acids build up."),
    "MIN": ("Minerals", "Adds calcium and sulphur, which fungi need a lot of."),
    "AIR": ("Air space", "Keeps particles apart so the mycelium can breathe."),
    "WATER": ("Water retention", "Holds water like a sponge."),
}
# wood form -> (name, typical size, what it means); consensus values
WOOD_FORMS = {
    "WOOD_LOG": ("Logs and plugs", "whole logs or dowels", "no mix, no supplements"),
    "WOOD_CHOPPED": ("Chopped wood", "pieces bigger than the biggest chips", "big air pockets, dries out"),
    "WOOD_CHIP": ("Wood chips", "1-10 cm long, under 5 cm thick", "good air pockets, holds little water"),
    "WOOD_SHAVING": ("Wood shavings", "flakes 1-5 cm long, under 3 mm thick (animal bedding)",
                     "airy, holds water better than chips"),
    "WOOD_DUST": ("Sawdust", "particles under 3 mm", "holds water, packs tight, needs Air space and Protein boost"),
}
MAIN_CATEGORIES = ("STRAW", "HUSK")          # plus every WOOD_* category
RISKY_UNSTERILISED = ("PROT", "QSUR")        # start unticked unless the mix is autoclaved
SOFTWOOD_NOTE = "Softwoods contain natural defensive compounds against fungi that can cause slower growth."
DEFAULT_MAIN = "beech_sawdust"

# method key -> (label, protocol_id in protocol.csv or None, instruction)
METHODS = {
    "STER": ("Autoclave / pressure cooker, 121 °C (15 psi)", "STER", ""),
    "STEAM": ("Steam (pot or barrel with lid)", "PAST",
              "Soak 12 h or more, then steam at a rolling boil (about 100 °C) for about 2 h."),
    "COLD": ("Cold pasteurisation (lime soak)", None,
             "Soak in water with hydrated lime, about 2-4 g per litre, for 12-18 h, then drain."),
}
# autoclave size key -> (label, minutes or None)
AUTOCLAVE_SIZES = {
    "under_1l": ("Under 1 L", 20),
    "up_to_1kg": ("Grain jars or bags up to 1 kg", 90),
    "1_to_3kg": ("Bags 1-3 kg", 150),
    "over_3kg": ("Over 3 kg", None),
}
OVER_3KG_MESSAGE = "Split into bags of 3 kg or less, or use cold pasteurisation."

# % of dry weight offered for a supplement the guide row does not name (consensus starting points)
DEFAULT_PCT = {"wheat_bran": 15.0, "rice_bran": 15.0, "soybean_meal": 5.0, "cottonseed_meal": 5.0,
               "corn_meal": 5.0, "gypsum": 1.0, "chalk": 1.0, "hydrated_lime": 1.0}

# guide words -> ingredient (None = a log: no mix ingredient); the earliest word in a phrase wins
_GUIDE_WORDS = [
    (r"\blogs?\b|\bbillets?\b", None),
    (r"hardwood sawdust|\bsawdust\b|\bbeech\b", "beech_sawdust"),
    (r"cereal straw|wheat straw", "wheat_straw"),
    (r"\bpaddy\b|rice straw", "rice_straw"),
    (r"\bstraw\b", "wheat_straw"),
    (r"\bwheat\b(?=[ /a-z]*\bbran\b)", "wheat_bran"),
    (r"\brice\b(?=[ /a-z]*\bbran\b)", "rice_bran"),
    (r"cottonseed meal", "cottonseed_meal"),
    (r"cottonseed hulls?", "cottonseed_hulls"),
    (r"cotton waste", "cotton_mill_waste"),
    (r"soybean meal|soy meal", "soybean_meal"),
    (r"soybean hulls?|soy hulls?", "soy_hull"),
    (r"corncobs?", "corncobs"),
    (r"corn meal|cornmeal", "corn_meal"),
    (r"bagasse", "sugarcane_bagasse"),
    (r"gypsum|caso4", "gypsum"),
    (r"hydrated lime|ca\(oh\)2", "hydrated_lime"),
    (r"caco3|\bchalk\b|garden lime|\blime\b", "chalk"),
]
_PCT = re.compile(r"(\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?\s*%")


@lru_cache(maxsize=1)
def load() -> pd.DataFrame:
    """The ingredient table, indexed by ingredient id; text columns empty instead of NaN."""
    df = pd.read_csv(INGREDIENTS_CSV, dtype={"wood_type": str, "group_1": str, "group_2": str})
    for c in ("display_name", "category", "wood_type", "group_1", "group_2", "value_source", "basis"):
        df[c] = df[c].fillna("")
    return df.set_index("ingredient", drop=False)


def name(ingredient: str) -> str:
    df = load()
    return df.at[ingredient, "display_name"] if ingredient in df.index else ingredient


def is_main(category: str) -> bool:
    return category.startswith("WOOD_") or category in MAIN_CATEGORIES


def is_pleurotus(species) -> bool:
    return str(species or "").strip().lower().startswith("pleurotus")


def main_options(species) -> list[str]:
    """Main-material ingredient ids, table order; softwood rows only for oyster species (Pleurotus)."""
    df = load()
    ok = df["category"].map(is_main) & ((df["wood_type"] != "soft") | is_pleurotus(species))
    return df.index[ok].tolist()


def form_caption(ingredient: str) -> str:
    """'Sawdust: particles under 3 mm; holds water, ...' for a wood row, '' otherwise."""
    df = load()
    if ingredient not in df.index or df.at[ingredient, "category"] not in WOOD_FORMS:
        return ""
    label, size, meaning = WOOD_FORMS[df.at[ingredient, "category"]]
    return f"{label}: {size}; {meaning}."


def supplement_groups() -> dict[str, list[str]]:
    """{group code: [ingredient ids with that group_1]} for the supplement groups (not BASE), GROUPS order;
    groups without an ingredient are left out."""
    df = load()
    out = {g: df.index[df["group_1"] == g].tolist() for g in GROUPS}
    return {g: ids for g, ids in out.items() if ids}


def guide_substrate_code(ingredient) -> str:
    """The consensus guide's substrate_code for a main material (baseline_guide.row falls back to sawdust)."""
    special = {"cottonseed_hulls": "cotton", "sugarcane_bagasse": "bagasse", "corncobs": "corncob"}
    df = load()
    if ingredient in special:
        return special[ingredient]
    if ingredient not in df.index:
        return "sawdust"
    cat = df.at[ingredient, "category"]
    if cat == "WOOD_LOG":
        return "logs"
    return "sawdust" if cat.startswith("WOOD_") else "straw"


def _words(text) -> list:
    """Ingredient ids named in text, in the order they appear (None for a log); one entry per position."""
    s = str(text or "").lower()
    hits = sorted(((m.start(), -m.end(), ing) for pattern, ing in _GUIDE_WORDS for m in re.finditer(pattern, s)),
                  key=lambda h: (h[0], h[1]))
    out, end = [], -1
    for start, neg_end, ing in hits:              # earliest, longest first; words inside a match are skipped
        if start < end:
            continue
        end = -neg_end
        if ing not in out:
            out.append(ing)
    return out


def match_guide_words(text):
    """The ingredient the guide's words name ('hardwood sawdust' -> beech_sawdust, 'CaCO3' -> chalk, ...);
    the first one when several are named; None for unknown words or logs (they stay text, add nothing to C:N)."""
    words = _words(text)
    return words[0] if words else None


def split_top_level(text: str) -> list[str]:
    """Split on commas outside brackets: '15% bran, 1% CaCO3 (chalk, lime)' -> 2 parts."""
    parts, depth, cur = [], 0, ""
    for ch in text:
        depth += (ch == "(") - (ch == ")")
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return [p.strip() for p in parts if p.strip()]


def guide_supplements(text) -> tuple[dict[str, dict], list[str]]:
    """The guide's supplementation text -> ({ingredient: {'pct', 'ticked'}}, [text the table cannot use]).

    pct = midpoint of a range. 'A or B' (also 'wheat/rice bran'): both get the amount, only the first is ticked;
    'None or A': A gets the amount, unticked."""
    if not isinstance(text, str) or not text.strip():
        return {}, []
    found, left = {}, []
    for part in split_top_level(text):
        m = _PCT.search(part)
        words = [w for w in _words(part) if w]
        if not m or not words:
            left.append(part)
            continue
        low = float(m.group(1))
        pct = (low + float(m.group(2) or low)) / 2
        optional = part.lower().startswith("none or")
        for k, ing in enumerate(words):
            found.setdefault(ing, {"pct": pct, "ticked": k == 0 and not optional})
    return found, left


def default_ticked(ingredient: str, method: str, in_guide: bool) -> bool:
    """Ticked if the guide names it; Protein boost and Quick energy start unticked unless autoclaved."""
    if not in_guide:
        return False
    df = load()
    risky = ingredient in df.index and df.at[ingredient, "group_1"] in RISKY_UNSTERILISED
    return not (risky and method != "STER")


def autoclave_time(size_key: str):
    """(minutes or None, text) for one jar or bag at 121 °C."""
    label, minutes = AUTOCLAVE_SIZES[size_key]
    if minutes is None:
        return None, OVER_3KG_MESSAGE
    shown = f"{minutes} min" if minutes < 120 else f"{minutes / 60:g} h"
    return minutes, f"{label}: {shown} at 121 °C (15 psi)."


def autoclave_size_key(litres=None, damp_kg=None) -> str:
    """Size key from the vessel: under 1 L by volume, else by damp weight; 'up_to_1kg' when nothing is known."""
    if litres is not None and litres < 1:
        return "under_1l"
    if damp_kg is None or damp_kg <= 1:
        return "up_to_1kg"
    return "1_to_3kg" if damp_kg <= 3 else "over_3kg"


def mix_cn(parts: dict[str, float]):
    """C:N of a dry mix {ingredient: dry weight} = sum(w x C%) / sum(w x N%); minerals add weight only.
    Unknown ingredients add nothing. None when the mix has no nitrogen."""
    df = load()
    c = n = 0.0
    for ing, w in parts.items():
        if ing in df.index and w:
            c += w * float(df.at[ing, "C_pct_dry"])
            n += w * float(df.at[ing, "N_pct_dry"])
    return c / n if n > 0 else None


def uses_category_values(parts) -> bool:
    df = load()
    return any(ing in df.index and df.at[ing, "value_source"] == "category" for ing in parts)
