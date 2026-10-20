# dsr_mycodemo

A grow planner for mushrooms and mycelium materials (demo at DSR). Pick what to grow, describe where you grow it, and the app gives a starter recipe, a stage timeline (colonisation, then fruiting), warnings, and a Monitor page where you log photos, conditions and harvests. Photos update the colonisation forecast. The app gives no yield estimate: you record your own harvest in Monitor.

Timings, stages, growing conditions and recipes come from a consensus of mycology and agricultural-science sources: `data/processed/cultivation_baseline.csv`. Other sources of ideas are listed in `THIRD_PARTY_NOTICES.md`.

## Run

```bash
uv venv --python 3.13 && source .venv/bin/activate
uv pip install -e .
streamlit run dsr_mycodemo/app/Welcome.py
python -m pytest -q
```

## Layout

- `dsr_mycodemo/app/`: the Streamlit app (Welcome and pages).
- `dsr_mycodemo/pipeline.py`: one batch in, recipe, dates, warnings and outcome out.
- `dsr_mycodemo/cultivation/`: the consensus table lookup (`baseline_guide.py`) and recipe maths (`recipe.py`).
- `dsr_mycodemo/growth/`: colonisation estimate, photo coverage and forecast.
- `data/`: the data files the app reads (the folder is git-ignored; files are added with `git add -f`).
- `models/colonisation/`: the saved colonisation estimate model.
- `tests/`: pytest.
