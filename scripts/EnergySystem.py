from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from core.builder_config import MAIN_DB_PATH, TABULA_XLSX_PATH
from core.dataSources import *
from core.db_utils import TableBatch, connect, write_table_batch
from core.excel_utils import build_rows, read_excel_sheet


START_ROW = 10


@dataclass(frozen=True, slots=True)
class SheetLoadSpec:
    table_name: str
    create_sql: str
    insert_sql: str
    sheet_name: str
    row_builder: Callable[[Any, int], list[object] | None]


def normalize_start_year(value):
    if value == "nan" or type(value) == float or type(value) == str:
        return 0
    return value


def normalize_end_year(value):
    if value == "nan" or type(value) == float or type(value) == str:
        return 9999
    return value


def build_heating_system_row(table, index: int) -> list[object]:
    return [
        None,
        table.at[index, "Code_SysH"],
        table.at[index, "Code_Country"],
        table.at[index, "CombiCode_SysH_EC"],
        table.at[index, "CombiCode_SysH_G"],
        table.at[index, "Description_SysH"],
        table.at[index, "Description_National_SysH"],
        table.at[index, "Code_SysH_EC1"],
        table.at[index, "Code_SysH_EC2"],
        table.at[index, "Code_SysH_G1"],
        table.at[index, "Code_SysH_G2"],
        table.at[index, "Code_SysH_G3"],
        table.at[index, "Fraction_SysH_G2"],
        table.at[index, "Fraction_SysH_G3"],
        table.at[index, "Code_SysH_S"],
        table.at[index, "Code_SysH_D"],
        table.at[index, "Code_SysH_Aux"],
    ]


def build_component_row(
    table,
    index: int,
    code_key: str,
    type_key: str,
    description_key: str,
    description_national_key: str,
    remark_key: str,
    first_year_key: str,
    last_year_key: str,
    value_keys: list[str],
) -> list[object]:
    first_year = normalize_start_year(table.at[index, first_year_key])
    last_year = normalize_end_year(table.at[index, last_year_key])

    row = [
        None,
        table.at[index, code_key],
        table.at[index, "Code_Country"],
        table.at[index, type_key],
        table.at[index, "Code_BuildingSizeClass_System"],
        table.at[index, description_key],
        table.at[index, description_national_key],
        table.at[index, remark_key],
        first_year,
        last_year,
    ]
    row.extend(table.at[index, value_key] for value_key in value_keys)
    return row


def build_water_heating_system_row(table, index: int) -> list[object]:
    return [
        None,
        table.at[index, "Code_SysW"],
        table.at[index, "Code_Country"],
        table.at[index, "CombiCode_SysW_EC"],
        table.at[index, "CombiCode_SysW_G"],
        table.at[index, "Description_SysW"],
        table.at[index, "Description_National_SysW"],
        table.at[index, "Code_SysW_EC1"],
        table.at[index, "Code_SysW_EC2"],
        table.at[index, "Code_SysW_EC3"],
        table.at[index, "Code_SysW_G1"],
        table.at[index, "Code_SysW_G2"],
        table.at[index, "Code_SysW_G3"],
        table.at[index, "Fraction_SysW_G2"],
        table.at[index, "Fraction_SysW_G3"],
        table.at[index, "Code_SysW_S"],
        table.at[index, "Code_SysW_D"],
        table.at[index, "Code_SysW_Aux"],
    ]


def build_specs() -> list[SheetLoadSpec]:
    return [
        SheetLoadSpec(
            TABULA_HEATING_SYSTEM,
            f"""CREATE TABLE IF NOT EXISTS {TABULA_HEATING_SYSTEM} (
                id integer primary key,
                code varchar,
                country varchar,
                combination_e_carrier varchar,
                combination_heat_generator varchar,
                description varchar,
                description_national varchar,
                code_ec1 varchar,
                code_ec2 varchar,
                code_g1 varchar,
                code_g2 varchar,
                code_g3 varchar,
                fraction_g2 varchar,
                fraction_g3 varchar,
                code_storage varchar,
                code_distribution varchar,
                code_aux varchar
            )""",
            f"INSERT INTO {TABULA_HEATING_SYSTEM} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "Tab.System.H",
            build_heating_system_row,
        ),
        SheetLoadSpec(
            TABULA_HEATING_SYSTEM_GENERATOR,
            f"""CREATE TABLE IF NOT EXISTS {TABULA_HEATING_SYSTEM_GENERATOR} (
                id integer primary key,
                code varchar,
                country varchar,
                type varchar,
                building_size_class varchar,
                description varchar,
                description_national varchar,
                remark varchar,
                first_year integer,
                last_year integer,
                e_g_h_heat real,
                e_g_h_electricity real
            )""",
            f"INSERT INTO {TABULA_HEATING_SYSTEM_GENERATOR} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "Tab.System.HG",
            lambda table, index: build_component_row(
                table, index, "Code_SysHG", "Code_Type_SysHG", "Description_SysHG",
                "Description_National_SysHG", "Remark_SysHG", "year1_SysHG", "year2_SysHG",
                ["e_g_h_Heat", "e_g_h_Electricity"],
            ),
        ),
        SheetLoadSpec(
            TABULA_HEATING_SYSTEM_STORAGE,
            f"""CREATE TABLE IF NOT EXISTS {TABULA_HEATING_SYSTEM_STORAGE} (
                id integer primary key,
                code varchar,
                country varchar,
                type varchar,
                building_size_class varchar,
                description varchar,
                description_national varchar,
                remark varchar,
                first_year integer,
                last_year integer,
                q_s_h real
            )""",
            f"INSERT INTO {TABULA_HEATING_SYSTEM_STORAGE} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "Tab.System.HS",
            lambda table, index: build_component_row(
                table, index, "Code_SysHS", "Code_Type_SysHS", "Description_SysHS",
                "Description_National_SysHS", "Remark_SysHS", "year1_SysHS", "year2_SysHS",
                ["q_s_h"],
            ),
        ),
        SheetLoadSpec(
            TABULA_HEATING_SYSTEM_DISTRIBUTION,
            f"""CREATE TABLE IF NOT EXISTS {TABULA_HEATING_SYSTEM_DISTRIBUTION} (
                id integer primary key,
                code varchar,
                country varchar,
                type varchar,
                building_size_class varchar,
                description varchar,
                description_national varchar,
                remark varchar,
                first_year integer,
                last_year integer,
                q_d_h real
            )""",
            f"INSERT INTO {TABULA_HEATING_SYSTEM_DISTRIBUTION} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "Tab.System.HD",
            lambda table, index: build_component_row(
                table, index, "Code_SysHD", "Code_Type_SysHD", "Description_SysHD",
                "Description_National_SysHD", "Remark_SysHD", "year1_SysHD", "year2_SysHD",
                ["q_d_h"],
            ),
        ),
        SheetLoadSpec(
            TABULA_HEATING_SYSTEM_AUXILIARY,
            f"""CREATE TABLE IF NOT EXISTS {TABULA_HEATING_SYSTEM_AUXILIARY} (
                id integer primary key,
                code varchar,
                country varchar,
                type varchar,
                building_size_class varchar,
                description varchar,
                description_national varchar,
                remark varchar,
                first_year integer,
                last_year integer,
                q_del_h_aux real
            )""",
            f"INSERT INTO {TABULA_HEATING_SYSTEM_AUXILIARY} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "Tab.System.HA",
            lambda table, index: build_component_row(
                table, index, "Code_AuxH", "Code_Type_AuxH", "Description_AuxH",
                "Description_National_AuxH", "Remark_AuxH", "year1_AuxH", "year2_AuxH",
                ["q_del_h_aux"],
            ),
        ),
        SheetLoadSpec(
            TABULA_WATER_HEATING_SYSTEM,
            f"""CREATE TABLE IF NOT EXISTS {TABULA_WATER_HEATING_SYSTEM} (
                id integer primary key,
                code varchar,
                country varchar,
                combination_e_carrier varchar,
                combination_heat_generator varchar,
                description varchar,
                description_national varchar,
                code_ec1 varchar,
                code_ec2 varchar,
                code_ec3 varchar,
                code_g1 varchar,
                code_g2 varchar,
                code_g3 varchar,
                fraction_g2 varchar,
                fraction_g3 varchar,
                code_storage varchar,
                code_distribution varchar,
                code_aux varchar
            )""",
            f"INSERT INTO {TABULA_WATER_HEATING_SYSTEM} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "Tab.System.W",
            build_water_heating_system_row,
        ),
        SheetLoadSpec(
            TABULA_WATER_HEATING_SYSTEM_GENERATOR,
            f"""CREATE TABLE IF NOT EXISTS {TABULA_WATER_HEATING_SYSTEM_GENERATOR} (
                id integer primary key,
                code varchar,
                country varchar,
                type varchar,
                building_size_class varchar,
                description varchar,
                description_national varchar,
                remark varchar,
                first_year integer,
                last_year integer,
                e_g_w_Heat real,
                e_g_w_Electricity real
            )""",
            f"INSERT INTO {TABULA_WATER_HEATING_SYSTEM_GENERATOR} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "Tab.System.WG",
            lambda table, index: build_component_row(
                table, index, "Code_SysWG", "Code_Type_SysWG", "Description_SysWG",
                "Description_National_SysWG", "Remark_SysWG", "year1_SysWG", "year2_SysWG",
                ["e_g_w_Heat", "e_g_w_Electricity"],
            ),
        ),
        SheetLoadSpec(
            TABULA_WATER_HEATING_SYSTEM_STORAGE,
            f"""CREATE TABLE IF NOT EXISTS {TABULA_WATER_HEATING_SYSTEM_STORAGE} (
                id integer primary key,
                code varchar,
                country varchar,
                type varchar,
                building_size_class varchar,
                description varchar,
                description_national varchar,
                remark varchar,
                first_year integer,
                last_year integer,
                q_s_w real,
                q_s_w_h real
            )""",
            f"INSERT INTO {TABULA_WATER_HEATING_SYSTEM_STORAGE} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "Tab.System.WS",
            lambda table, index: build_component_row(
                table, index, "Code_SysWS", "Code_Type_SysWS", "Description_SysWS",
                "Description_National_SysWS", "Remark_SysWS", "year1_SysWS", "year2_SysWS",
                ["q_s_w", "q_s_w_h"],
            ),
        ),
        SheetLoadSpec(
            TABULA_WATER_HEATING_SYSTEM_DISTRIBUTION,
            f"""CREATE TABLE IF NOT EXISTS {TABULA_WATER_HEATING_SYSTEM_DISTRIBUTION} (
                id integer primary key,
                code varchar,
                country varchar,
                type varchar,
                building_size_class varchar,
                description varchar,
                description_national varchar,
                remark varchar,
                first_year integer,
                last_year integer,
                q_d_w real,
                q_d_w_h real
            )""",
            f"INSERT INTO {TABULA_WATER_HEATING_SYSTEM_DISTRIBUTION} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "Tab.System.WD",
            lambda table, index: build_component_row(
                table, index, "Code_SysWD", "Code_Type_SysWD", "Description_SysWD",
                "Description_National_SysWD", "Remark_SysWD", "year1_SysWD", "year2_SysWD",
                ["q_d_w", "q_d_w_h"],
            ),
        ),
        SheetLoadSpec(
            TABULA_WATER_HEATING_SYSTEM_AUXILIARY,
            f"""CREATE TABLE IF NOT EXISTS {TABULA_WATER_HEATING_SYSTEM_AUXILIARY} (
                id integer primary key,
                code varchar,
                country varchar,
                type varchar,
                building_size_class varchar,
                description varchar,
                description_national varchar,
                remark varchar,
                first_year integer,
                last_year integer,
                q_del_w_aux real
            )""",
            f"INSERT INTO {TABULA_WATER_HEATING_SYSTEM_AUXILIARY} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "Tab.System.WA",
            lambda table, index: build_component_row(
                table, index, "Code_AuxW", "Code_Type_AuxW", "Description_AuxW",
                "Description_National_AuxW", "Remark_AuxW", "year1_AuxW", "year2_AuxW",
                ["q_del_w_aux"],
            ),
        ),
    ]


def extract_source_table(sheet_name: str):
    return read_excel_sheet(TABULA_XLSX_PATH, sheet_name)


def transform_batch(spec: SheetLoadSpec) -> TableBatch:
    rows = build_rows(
        extract_source_table(spec.sheet_name),
        START_ROW,
        spec.row_builder,
    )
    return TableBatch(
        table_name=spec.table_name,
        create_sql=spec.create_sql,
        insert_sql=spec.insert_sql,
        rows=rows,
        error_message=f"{spec.table_name} insert error",
    )


def main() -> None:
    batches = [transform_batch(spec) for spec in build_specs()]

    with connect(MAIN_DB_PATH) as conn:
        cursor = conn.cursor()
        for batch in batches:
            write_table_batch(cursor, batch)
        conn.commit()


if __name__ == "__main__":
    main()
