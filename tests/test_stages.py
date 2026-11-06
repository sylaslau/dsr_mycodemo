"""The app's stage words map onto the one stage list in stage.csv."""

from dsr_mycodemo import pipeline, stages
from dsr_mycodemo.app import flow


def test_stage_csv_has_the_six_stages():
    assert stages.stage_ids() == ["ST1", "ST2", "ST3", "ST4", "ST5", "ST6"]
    assert stages.stage_name("ST6") == "Post-treatment"


def test_every_app_word_maps_to_a_known_stage_or_is_a_status():
    words = set(flow.STAGES_FOOD) | set(flow.STAGES_MATERIAL) | {w for row in _monitor_rows() for w in row}
    assert words <= set(stages.WORD_TO_STAGE)
    assert {stages.stage_of(w) for w in words} - {None} <= set(stages.stage_ids())
    assert stages.stage_of("Contaminated") is None


def test_colonising_words_are_st4_and_next_stage_words_follow():
    for goal, words in pipeline.COLONISING_STAGES.items():
        assert {stages.stage_of(w) for w in words} == {pipeline.COLONISING_STAGE_ID}
        assert stages.stage_of(pipeline.AFTER_COLONISATION[goal]) == pipeline.NEXT_STAGE_ID[goal]


def _monitor_rows():
    import ast
    from pathlib import Path
    src = (Path(flow.__file__).parent / "pages" / "4_Monitor.py").read_text()
    node = next(n for n in ast.parse(src).body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "STAGE_ROWS")
    return ast.literal_eval(node.value)
