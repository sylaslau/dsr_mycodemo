"""Welcome page (11-19): overview figure in place of the Food / Thing strips, short Data collection section."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).parents[1] / "dsr_mycodemo/app"


def test_welcome_shows_figure_and_data_collection():
    assert (APP / "images/app_overview.png").exists() and (APP / "images/shroom.png").exists()
    at = AppTest.from_file(str(APP / "Welcome.py"), default_timeout=60).run()
    assert not at.exception
    assert len(at.get("image")) == 2
    assert not at.columns and not at.expander
    assert [h.value for h in at.subheader] == ["Data collection"]
    text = " ".join(m.value for m in at.markdown)
    assert "We do not collect any personal data." in text
    assert "sf-box" not in text
