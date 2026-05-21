from __future__ import annotations

import os
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.builder_config import CRREM_OUTPUT_DB_PATH, CRREM_XLSX_PATH, MAIN_DB_PATH
from core.db_utils import connect


SHEET_CO2 = "2 - 1.5C CO2"
SHEET_KWH = "3 - 1.5 kWh"
SCENARIO_VALUE = "1.5°C"

REGION_LABELS = {"EUROPE", "Non Europe", "Australia"}

EU_LABEL_RE = re.compile(
    r"^\s*EU\s+(?P<asset>.+?)\s+(?P<metric>CO2-Int|CO2-INT|KWH-INT|kWh-Int)\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class CrremOutputs:
    co2_long: pd.DataFrame
    kwh_long: pd.DataFrame
    co2_out: pd.DataFrame
    kwh_out: pd.DataFrame


def find_data_start_row(df: pd.DataFrame) -> int:
    col0 = df.iloc[:, 0]

    def looks_like_year(value) -> bool:
        try:
            if value is None:
                return False
            if isinstance(value, float) and np.isnan(value):
                return False
            numeric_value = float(value)
            return 1900 <= numeric_value <= 2100 and numeric_value.is_integer()
        except Exception:
            return False

    for index, value in enumerate(col0.tolist()):
        if looks_like_year(value):
            return index

    raise ValueError("Cannot find data start row (year column) in sheet.")


def build_asset_series(row0: pd.Series) -> pd.Series:
    series = row0.copy()
    series = series.mask(series.isin(REGION_LABELS))
    series.iloc[0] = np.nan
    return series.ffill()


def parse_raw_code(raw_code: str):
    parts = str(raw_code).strip().split(".")
    if len(parts) < 3:
        return None, None, None

    geo = parts[0].strip()
    metric = parts[-1].strip()
    asset_class = ".".join(part.strip() for part in parts[1:-1] if part.strip())
    return geo, asset_class, metric


def parse_special_from_asset_label(asset_label: str):
    if not isinstance(asset_label, str):
        return None, None, None

    match = EU_LABEL_RE.match(asset_label)
    if not match:
        return None, None, None

    return "EU", match.group("asset").strip(), match.group("metric").strip()


def clean_asset_label_series(series: pd.Series) -> pd.Series:
    series = series.astype(str)
    series = series.str.replace(r"\bCO2\b", "", regex=True)
    series = series.str.replace(r"\bEUI\b", "", regex=True)
    series = series.str.replace(r"\s+", " ", regex=True).str.strip()
    return series


def extract_long_from_sheet(xlsx_path, sheet_name: str) -> pd.DataFrame:
    df = pd.read_excel(xlsx_path, sheet_name=sheet_name, header=None)

    data_start = find_data_start_row(df)
    header_rows = df.iloc[:data_start, :]
    data_rows = df.iloc[data_start:, :].reset_index(drop=True)

    if header_rows.shape[0] < 3:
        raise ValueError(f"Sheet '{sheet_name}' does not have expected 3 header rows.")

    row0 = header_rows.iloc[0, :]
    row1 = header_rows.iloc[1, :]
    unit = row0.iloc[0] if isinstance(row0.iloc[0], str) else str(row0.iloc[0])
    asset_series = build_asset_series(row0)

    years = pd.to_numeric(data_rows.iloc[:, 0], errors="coerce").astype("Int64")
    if years.isna().all():
        raise ValueError(f"Sheet '{sheet_name}': could not parse years from first column.")

    frames = []
    for column_index in range(1, data_rows.shape[1]):
        column_values = pd.to_numeric(data_rows.iloc[:, column_index], errors="coerce")
        if column_values.notna().sum() == 0:
            continue

        raw_code = row1.iloc[column_index]
        asset_label = asset_series.iloc[column_index]

        if isinstance(raw_code, str) and raw_code.strip():
            geo, _, _ = parse_raw_code(raw_code)
        else:
            geo, _, _ = parse_special_from_asset_label(asset_label)

        frames.append(
            pd.DataFrame(
                {
                    "country": geo,
                    "year": years,
                    "asset_label": asset_label,
                    "unit": unit,
                    "value": column_values,
                }
            )
        )

    long_df = pd.concat(frames, ignore_index=True)
    long_df = long_df.dropna(subset=["country", "year", "asset_label", "unit", "value"])
    long_df["year"] = pd.to_numeric(long_df["year"], errors="coerce").astype("Int64")
    long_df["value"] = pd.to_numeric(long_df["value"], errors="coerce")
    long_df = long_df.dropna(subset=["year", "value"])
    long_df["year"] = long_df["year"].astype(int)
    long_df["value"] = long_df["value"].astype(float).round(3)
    return long_df


def extract_sheet_outputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    return (
        extract_long_from_sheet(CRREM_XLSX_PATH, SHEET_CO2),
        extract_long_from_sheet(CRREM_XLSX_PATH, SHEET_KWH),
    )


def transform_outputs(co2_long: pd.DataFrame, kwh_long: pd.DataFrame) -> CrremOutputs:
    co2_long = co2_long.copy()
    kwh_long = kwh_long.copy()

    co2_long["asset_label"] = clean_asset_label_series(co2_long["asset_label"])
    kwh_long["asset_label"] = clean_asset_label_series(kwh_long["asset_label"])

    co2_long["scenario"] = SCENARIO_VALUE
    kwh_long["scenario"] = SCENARIO_VALUE

    co2_out = co2_long[["country", "year", "asset_label", "scenario", "value", "unit"]].copy()
    kwh_out = kwh_long[["country", "year", "asset_label", "scenario", "value", "unit"]].copy()

    return CrremOutputs(
        co2_long=co2_long,
        kwh_long=kwh_long,
        co2_out=co2_out,
        kwh_out=kwh_out,
    )


def create_output_db(outputs: CrremOutputs) -> None:
    if os.path.exists(CRREM_OUTPUT_DB_PATH):
        os.remove(CRREM_OUTPUT_DB_PATH)

    with connect(CRREM_OUTPUT_DB_PATH) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS co2_pathways (
                id INTEGER PRIMARY KEY,
                country TEXT,
                year INTEGER,
                asset_label TEXT,
                scenario TEXT,
                value REAL,
                unit TEXT
            );

            CREATE TABLE IF NOT EXISTS kwh_pathways (
                id INTEGER PRIMARY KEY,
                country TEXT,
                year INTEGER,
                asset_label TEXT,
                scenario TEXT,
                value REAL,
                unit TEXT
            );
            """
        )

        outputs.co2_out.to_sql("co2_pathways", conn, if_exists="append", index=False)
        outputs.kwh_out.to_sql("kwh_pathways", conn, if_exists="append", index=False)


def copy_into_main_db() -> None:
    with connect(MAIN_DB_PATH) as conn:
        conn.execute("ATTACH DATABASE ? as crrem", (str(CRREM_OUTPUT_DB_PATH),))
        conn.executescript(
            """
            BEGIN;

            DROP TABLE IF EXISTS crrem_1_5C_co2;
            CREATE TABLE crrem_1_5C_co2 (
                id INTEGER PRIMARY KEY,
                country TEXT,
                year INTEGER,
                asset_label TEXT,
                scenario TEXT,
                value REAL,
                unit TEXT
            );
            INSERT INTO crrem_1_5C_co2 (id, country, year, asset_label, scenario, value, unit)
            SELECT id, country, year, asset_label, scenario, value, unit
            FROM crrem.co2_pathways;

            DROP TABLE IF EXISTS crrem_1_5C_kwh;
            CREATE TABLE crrem_1_5C_kwh (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country TEXT,
                year INTEGER,
                asset_label TEXT,
                scenario TEXT,
                value REAL,
                unit TEXT
            );
            INSERT INTO crrem_1_5C_kwh (id, country, year, asset_label, scenario, value, unit)
            SELECT id, country, year, asset_label, scenario, value, unit
            FROM crrem.kwh_pathways;

            COMMIT;
            """
        )
        conn.execute("DETACH DATABASE crrem;")


def main() -> None:
    outputs = transform_outputs(*extract_sheet_outputs())

    create_output_db(outputs)

    copy_into_main_db()


if __name__ == "__main__":
    main()
