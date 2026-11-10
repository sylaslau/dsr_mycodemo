"""Recipe page (3) click-through by Streamlit AppTest: steps per method, vessel from page 2, one stacked figure."""

import re
from pathlib import Path

import pytest

PAGE = str(Path(__file__).parents[1] / "dsr_mycodemo/app/pages/3_Recipe_and_timeline.py")


def run_page(method, vessel=None, litres=None, amount=1, choice="Pleurotus ostreatus"):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(PAGE, default_timeout=60)
    s = at.session_state
    s["goal"], s["choice"], s["temp_c"] = "Food", choice, 22.0
    s["environment"], s["env_where"] = "Small plastic container (about 1 L)", "Plastic container"
    if vessel:
        s["env_container"], s["env_size"], s["env_amount"] = vessel, {vessel: litres}, {vessel: amount}
    s["rc_method"] = method
    at.run()
    assert not at.exception
    return at


def steps(at):
    return [m.value for m in at.markdown if m.value.startswith("#### ")]


def texts(at):
    return [m.value for m in at.markdown]


@pytest.mark.parametrize("method, first, second", [
    ("STER", "#### 1. Build your recipe, weigh, mix and fill vessels", "#### 2. Sterilise"),
    ("STEAM", "#### 1. Build your recipe and weigh the dry ingredients", "#### 2. Pasteurise"),
    ("COLD", "#### 1. Build your recipe", "#### 2. Lime soak"),
])
def test_steps_in_method_order_and_water_row_only_for_autoclave(method, first, second):
    at = run_page(method, "Glass Jar", 1.0, 3)
    assert steps(at)[:2] == [first, second] and steps(at)[2].startswith("#### 3.")
    assert ("Water" in texts(at)) is (method == "STER")
    assert at.radio[0].label == "Sterilisation method"
    assert not any(sb.label == "Size of each jar or bag" for sb in at.selectbox)
    assert not any("Treatment method" in t or "Amounts to weigh" in t for t in texts(at))


def test_glass_jar_from_page2_sets_the_autoclave_time():
    assert any(t.startswith("Your 0.5 L glass jar,") and "60 min" in t for t in texts(run_page("STER", "Glass Jar", 0.5)))
    assert any(t.startswith("Your 1 L glass jars,") and "90 min" in t
               for t in texts(run_page("STER", "Glass Jar", 1.0, 3)))
    assert "Choose a vessel on Environment." in [i.value for i in run_page("STER").info]


def test_grow_bag_table_switches_to_kg():
    at = run_page("STER", "Grow bag", 5.0, 4)
    weights = [t for t in texts(at) if re.fullmatch(r"\*{0,2}[\d.]+ k?g\*{0,2}", t)]
    assert weights and all(w.strip("*").endswith(" kg") for w in weights)
    small = run_page("STER", "Glass Jar", 0.5)
    assert all(w.strip("*").endswith(" g") for w in texts(small) if re.fullmatch(r"\*{0,2}[\d.]+ k?g\*{0,2}", w))


def test_lime_soak_starts_with_main_bulk_only():
    at = run_page("COLD", "Grow bag", 5.0, 2)
    assert not any(c.value for c in at.checkbox)


def test_one_stacked_figure_and_five_bubbles_without_subtext():
    at = run_page("STER", "Glass Jar", 1.0, 3)
    charts = at.get("plotly_chart")
    assert len(charts) == 1
    bubbles = [t for t in texts(at) if "border-left:8px" in t]
    assert [re.search(r"<b>(\w+)</b>", b).group(1) for b in bubbles] == [
        "Inoculation", "Colonising", "Induction", "Fruiting", "Harvest"]
    assert all("🌡️" in b and "💧" in b and "🌬️" in b and "💡" in b for b in bubbles)
    assert all("white all the way through" not in t for t in texts(at))
