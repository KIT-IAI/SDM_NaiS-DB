from __future__ import annotations

from core.builder_config import MAIN_DB_PATH, TABULA_XLSX_PATH
from core.dataSources import TABULA_CALCULATION_BUILDING_SET
from core.db_utils import TableBatch, connect, write_table_batch
from core.excel_utils import read_excel_sheet


SHEET_NAME = "Calc.Building.Set"
START_ROW = 11

CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABULA_CALCULATION_BUILDING_SET} (
    id integer primary key,
    code varchar,
    country varchar,
    building varchar,
    type_variant varchar,
    description varchar,
    description_national varchar,
    building_type varchar,
    dataType_building varchar,
    building_size_class varchar,
    construction_year_class varchar,
    first_year int,
    last_year int,
    area real,
    area_roof_1 real,
    area_roof_2 real,
    area_wall_1 real,
    area_wall_2 real,
    area_wall_3 real,
    area_floor_1 real,
    area_floor_2 real,
    area_window_1 real,
    area_window_2 real,
    area_door_1 real,
    uv_roof_1 real,
    uv_roof_2 real,
    uv_wall_1 real,
    uv_wall_2 real,
    uv_wall_3 real,
    uv_floor_1 real,
    uv_floor_2 real,
    uv_window_1 real,
    uv_window_2 real,
    uv_door_1 real
)
"""

COLUMN_NAMES = [
    "Code_BuildingVariant",
    "Code_Country",
    "Code_Building",
    "Code_TypeVariant",
    "Description_BuildingVariant",
    "Description_BuildingVariant_National",
    "Code_BuildingType",
    "Code_DataType_Building",
    "Code_BuildingSizeClass",
    "Code_ConstructionYearClass",
    "Year1_Building",
    "Year2_Building",
    "A_C_Ref",
    "A_Roof_1",
    "A_Roof_2",
    "A_Wall_1",
    "A_Wall_2",
    "A_Wall_3",
    "A_Floor_1",
    "A_Floor_2",
    "A_Window_1",
    "A_Window_2",
    "A_Door_1",
    "U_Roof_1",
    "U_Roof_2",
    "U_Wall_1",
    "U_Wall_2",
    "U_Wall_3",
    "U_Floor_1",
    "U_Floor_2",
    "U_Window_1",
    "U_Window_2",
    "U_Door_1",
]


def extract_source_table():
    return read_excel_sheet(TABULA_XLSX_PATH, SHEET_NAME)


def transform_rows(table) -> list[list[object]]:
    rows: list[list[object]] = []
    for index in range(START_ROW, len(table)):
        rows.append([None, *[table.at[index, column_name] for column_name in COLUMN_NAMES]])
    return rows


def build_table_batch(rows: list[list[object]]) -> TableBatch:
    return TableBatch(
        table_name=TABULA_CALCULATION_BUILDING_SET,
        create_sql=CREATE_SQL,
        insert_sql=f"INSERT INTO {TABULA_CALCULATION_BUILDING_SET} VALUES ({', '.join(['?'] * 34)})",
        rows=rows,
        error_message="tabula calculation set table insert error",
    )


def main() -> None:
    batch = build_table_batch(transform_rows(extract_source_table()))

    with connect(MAIN_DB_PATH) as conn:
        cursor = conn.cursor()
        write_table_batch(cursor, batch)
        conn.commit()


if __name__ == "__main__":
    main()
