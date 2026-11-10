"""references/supabase_schema.sql must keep the CSV headers of data/interim/extracted/ (same names, same order),
so the Supabase tables and the app's rows never drift from the data again."""

import csv
import re

import pytest

from dsr_mycodemo.config import INTERIM_DATA_DIR, PROJ_ROOT

SCHEMA = PROJ_ROOT / "references" / "supabase_schema.sql"
EXTRACTED = INTERIM_DATA_DIR / "extracted"
APP_TABLES = {"dataset", "sample", "fermentation", "substrate", "compartment", "process", "reading", "outcome",
              "image", "flag"}
NO_TABLE = {"stage", "protocol", "measure", "growth_parameter",
            "cn_ingredients"}   # code lists / literature / lookups: never sent by growers


def schema_tables():
    """{table: [columns in order]} from the create table blocks."""
    sql = SCHEMA.read_text()
    tables = {}
    for name, body in re.findall(r"create table public\.(\w+) \((.*?)\n\);", sql, re.S):
        tables[name] = [line.split()[0] for line in body.strip().splitlines()
                        if line.strip() and not line.strip().startswith("primary key")]
    return tables


def header(table):
    with open(EXTRACTED / f"{table}.csv", encoding="utf-8-sig") as f:
        return next(csv.reader(f))


def test_schema_has_the_app_tables():
    assert set(schema_tables()) == APP_TABLES


@pytest.mark.parametrize("table", sorted(APP_TABLES))
def test_columns_equal_csv_header(table):
    if not (EXTRACTED / f"{table}.csv").exists():
        pytest.skip(f"{table}: no CSV in data/interim/extracted/")
    assert schema_tables()[table] == header(table)


def test_every_csv_is_a_table_or_a_known_code_list():
    csvs = {p.stem for p in EXTRACTED.glob("*.csv")}
    assert csvs - APP_TABLES <= NO_TABLE, csvs - APP_TABLES - NO_TABLE
