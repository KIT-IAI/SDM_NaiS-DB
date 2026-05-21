from __future__ import annotations

from dataclasses import dataclass

import openpyxl

from core.builder_config import IWU_XLSX_PATH, MAIN_DB_PATH
from core.dataSources import IWU_NWG
from core.db_utils import TableBatch, connect, write_table_batch


CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {IWU_NWG} (
    id integer primary key,
    building_function varchar,
    building_element varchar,
    first_year integer,
    last_year integer,
    u_value real
)
"""


@dataclass(frozen=True, slots=True)
class SheetSpec:
    sheet_name: str
    building_element: str


@dataclass(frozen=True, slots=True)
class YearColumnSpec:
    column_name: str
    first_year: int
    last_year: int


SHEET_SPECS = (
    SheetSpec("U_AW_mfl", "Außenwand"),
    SheetSpec("U_d_opak_mfl", "Opakes Dach"),
    SheetSpec("U_Fen_mfl", "Fenster"),
    SheetSpec("U_ug_mfl", "Boden"),
)

YEAR_COLUMN_SPECS = (
    YearColumnSpec("B", 0, 1978),
    YearColumnSpec("F", 1979, 2009),
    YearColumnSpec("J", 2010, 9999),
)


def extract_workbook():
    return openpyxl.load_workbook(IWU_XLSX_PATH)


def format_u_value(value) -> str:
    return "{:.2f}".format(value)


def transform_rows(workbook) -> list[list[object]]:
    rows: list[list[object]] = []
    for sheet_spec in SHEET_SPECS:
        sheet = workbook[sheet_spec.sheet_name]
        for row_index in range(5, 16):
            building_function = sheet[f"A{row_index}"].value
            for year_column in YEAR_COLUMN_SPECS:
                u_value = format_u_value(sheet[f"{year_column.column_name}{row_index}"].value)
                rows.append(
                    [
                        None,
                        building_function,
                        sheet_spec.building_element,
                        year_column.first_year,
                        year_column.last_year,
                        u_value,
                    ]
                )
    return rows


def build_table_batch(rows: list[list[object]]) -> TableBatch:
    return TableBatch(
        table_name=IWU_NWG,
        create_sql=CREATE_SQL,
        insert_sql=f"INSERT INTO {IWU_NWG} VALUES (?, ?, ?, ?, ?, ?)",
        rows=rows,
        error_message="iwu_nwg insert error",
    )


def main() -> None:
    batch = build_table_batch(transform_rows(extract_workbook()))

    with connect(MAIN_DB_PATH) as conn:
        cursor = conn.cursor()
        write_table_batch(cursor, batch)
        conn.commit()


if __name__ == "__main__":
    main()
