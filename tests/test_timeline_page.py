"""Timeline (was Calendar and tasks, 11-18): the figure, stage bubbles and dates moved from Recipe, the fruiting dates
once induction is confirmed, then the calendar and tasks previews."""

import re
from datetime import date
from pathlib import Path

from dsr_mycodemo import pipeline

PAGE = str(Path(__file__).parents[1] / "dsr_mycodemo/app/pages/3_Timeline.py")
START = date(2026, 10, 8)
PLAN = {"batch_label": "B1", "species": "Pleurotus ostreatus", "inoc_date": START, "n_containers": 2,
        "temp_c": 22.0, "substrate": "sawdust", "spawn_pct": 10.0}


def _page(goal="Food", choice="Pleurotus ostreatus", **state):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(PAGE, default_timeout=60)
    s = at.session_state
    s["goal"], s["choice"], s["temp_c"], s["inoc_date"] = goal, choice, 22.0, START
    s["material_species"] = "Trametes versicolor"
    s["environment"], s["env_where"] = "Small plastic container (about 1 L)", "Plastic container"
    s["batch"] = PLAN
    for k, v in state.items():
        s[k] = v
    at.run()
    assert not at.exception, at.exception
    return at


def _md(at):
    return [m.value for m in at.markdown]


def test_figure_bubbles_and_dates_on_timeline():
    at = _page()
    assert at.title[0].value == "Timeline"
    assert len(at.get("plotly_chart")) == 1
    bubbles = [t for t in _md(at) if "border-left:8px" in t]
    assert [re.search(r"<b>(\w+)</b>", b).group(1) for b in bubbles] == [
        "Inoculation", "Colonising", "Induction", "Fruiting", "Harvest"]
    assert all("🌡️" in b and "💧" in b and "🌬️" in b and "💡" in b for b in bubbles)
    assert "Current estimated timeline" in [s.value for s in at.subheader]
    # under the bubbles (11-19): Induction planning marker and duration only; no 90% box, bar, notes or warnings
    labels = [m.label for m in at.metric]
    assert pipeline.MARKER_LABEL in labels and pipeline.ENDPOINT_LABEL not in labels
    assert not at.get("progress") and not at.warning and not at.button
    assert not any("Project assumption" in c.value or "Your photos in Monitor" in c.value for c in at.caption)
    assert not any("colonisation range" in t for t in _md(at))
    assert "Fruiting dates" not in [s.value for s in at.subheader]
    cal = [t for t in _md(at) if "Calendar" in t and "PREVIEW" in t]
    assert len(cal) == 1 and cal[0].rstrip().endswith("</table></div>")
    assert not any("Tasks and reminders" in t or "Warnings" in t for t in _md(at))


def test_cold_plan_shows_no_temperature_line_or_warning():
    at = _page(temp_c=14.0, batch={**PLAN, "temp_c": 14.0})
    assert not at.warning and not at.success
    assert not any("colonisation range" in t for t in _md(at))


def test_fruiting_dates_once_induction_is_confirmed():
    at = _page(batch_stage="Fruiting", next_start=date(2026, 11, 2))
    assert "Fruiting dates" in [s.value for s in at.subheader]
    assert [m.label for m in at.metric][-3:] == ["Start of induction", "Pinning", "First harvest"]
    assert at.metric[-3].value == "02 Nov"


def test_materials_timeline_is_greyed():
    at = _page("Materials", "Packaging foam")
    assert not at.get("plotly_chart")
    assert " ".join(_md(at)).count(pipeline.MATERIALS_PREVIEW_NOTE) >= 3
