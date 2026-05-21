from __future__ import annotations

import statistics
from dataclasses import dataclass

from core.builder_config import MAIN_DB_PATH, TABULA_XLSX_PATH
from models.builidngType import BuildingType
from models.building import Building
from models.construction import Construction
from core.countries import countries
from core.dataSources import (
    TABULA_BUILDING,
    TABULA_BUILDING_TYPE,
    TABULA_CONSTRUCTION,
    TABULA_LOCATION,
    TABULA_YEAR_CLASS,
)
from core.db_utils import TableBatch, connect, safe_execute, write_table_batch
from core.excel_utils import read_excel_sheet
from models.yearClass import YearClass


LOCATION_SHEET = "Tab.TypologyRegion"
YEAR_CLASS_SHEET = "Tab.ConstrYearClass"
BUILDING_TYPE_SHEET = "Tab.Type.Building"
BUILDING_SHEET = "Tab.Building"
CONSTRUCTION_SHEET = "Tab.Building.Constr"


@dataclass(frozen=True, slots=True)
class SourceTables:
    locations: object
    year_classes: object
    building_types: object
    buildings: object
    constructions: object


@dataclass(frozen=True, slots=True)
class YearClassTransform:
    items: dict[str, YearClass]
    batch: TableBatch


@dataclass(frozen=True, slots=True)
class BuildingTypeTransform:
    items: dict[str, BuildingType]
    batch: TableBatch


@dataclass(frozen=True, slots=True)
class BuildingTransform:
    items: dict[str, Building]
    batch: TableBatch


@dataclass(frozen=True, slots=True)
class ConstructionTransform:
    items: dict[str, Construction]
    batch: TableBatch


LOCATION_CREATE_SQL = f"""create table if not exists {TABULA_LOCATION} (
    id integer primary key,
    code varchar,
    country varchar,
    country_code varchar,
    region_code varchar
)"""

YEAR_CLASS_CREATE_SQL = f"""create table if not exists {TABULA_YEAR_CLASS} (
    id integer primary key,
    code varchar,
    country_code varchar,
    first_year integer,
    last_year integer
)"""

BUILDING_TYPE_CREATE_SQL = f"""create table if not exists {TABULA_BUILDING_TYPE} (
    id integer primary key,
    code varchar,
    country varchar,
    region varchar,
    building_size_class varchar,
    building_size_class_ext varchar,
    average_area real,
    year_class varchar,
    year_class_ext,
    first_year integer,
    last_year integer,
    last_year_ext integer,
    building_functionality,
    data_source
)"""

BUILDING_CREATE_SQL = f"""create table if not exists {TABULA_BUILDING} (
    id integer primary key,
    code varchar,
    building_type varchar,
    data_type varchar,
    description varchar,
    ref_area real,
    code_roof_1 varchar,
    code_roof_2 varchar,
    code_wall_1 varchar,
    code_wall_2 varchar,
    code_wall_3 varchar,
    code_floor_1 varchar,
    code_floor_2 varchar,
    code_window_1 varchar,
    code_window_2 varchar,
    code_door_1 varchar
)"""

CONSTRUCTION_CREATE_SQL = f"""create table if not exists {TABULA_CONSTRUCTION} (
    id integer primary key,
    code varchar,
    country varchar,
    variant varchar,
    element_type varchar,
    name,
    name_national,
    description,
    description_national,
    first_year,
    last_year,
    u_value,
    d_insulation,
    g_value
)"""


def rounded_down_to_2_decimals(value) -> float:
    return float(int(value * 100) / 100)


def extract_source_tables() -> SourceTables:
    return SourceTables(
        locations=read_excel_sheet(TABULA_XLSX_PATH, LOCATION_SHEET),
        year_classes=read_excel_sheet(TABULA_XLSX_PATH, YEAR_CLASS_SHEET),
        building_types=read_excel_sheet(TABULA_XLSX_PATH, BUILDING_TYPE_SHEET),
        buildings=read_excel_sheet(TABULA_XLSX_PATH, BUILDING_SHEET),
        constructions=read_excel_sheet(TABULA_XLSX_PATH, CONSTRUCTION_SHEET),
    )


def transform_locations(table) -> TableBatch:
    rows: list[list[object]] = []

    for index in range(len(table)):
        if index < 10:
            continue

        code = table.at[index, "Code_TypologyRegion"]
        if code == "XX.N":
            continue

        country_code = table.at[index, "Code_Country"]
        country = countries[country_code]
        region_code = table.at[index, "ShortCut_TypologyRegion"]
        rows.append([None, code, country, country_code, region_code])

    return TableBatch(
        table_name=TABULA_LOCATION,
        create_sql=LOCATION_CREATE_SQL,
        insert_sql=f"insert into {TABULA_LOCATION} values (?, ?, ?, ?, ?)",
        rows=rows,
        error_message="tabula location table insert error",
    )


def transform_year_classes(table) -> YearClassTransform:
    items: dict[str, YearClass] = {}
    rows: list[list[object]] = []

    for index in range(len(table)):
        if index < 9:
            continue

        code = table.at[index, "Code_ConstructionYearClass"]
        prefix = code.split(".")[0]
        if prefix == "##" or prefix == "XX":
            continue

        country_code = table.at[index, "Code_Country"]
        first_year = table.at[index, "ConstructionYearClass_FirstYear"]
        last_year = table.at[index, "ConstructionYearClass_LastYear"]

        items[code] = YearClass(code, country_code, first_year, last_year)
        rows.append([None, code, country_code, first_year, last_year])

    return YearClassTransform(
        items=items,
        batch=TableBatch(
            table_name=TABULA_YEAR_CLASS,
            create_sql=YEAR_CLASS_CREATE_SQL,
            insert_sql=f"insert into {TABULA_YEAR_CLASS} values (?, ?, ?, ?, ?)",
            rows=rows,
            error_message="tabula year class table insert error",
        ),
    )


def transform_building_types(table, year_classes: dict[str, YearClass]) -> BuildingTypeTransform:
    items: dict[str, BuildingType] = {}
    rows: list[list[object]] = []

    for index in range(len(table)):
        if index < 9:
            continue

        country = table.at[index, "Code_Country"]
        if country == "##" or country == "XX":
            continue

        code = table.at[index, "Code_BuildingType"]
        region = table.at[index, "Code_TypologyRegion"]
        building_size_class = table.at[index, "Code_BuildingSizeClass"]
        building_size_class_ext = table.at[index, "Code_BuildingSizeClass_Extension"]
        year_class = table.at[index, "Code_ConstructionYearClass"]
        year_class_ext = table.at[index, "Code_ConstructionYearClass_Extension"]

        if year_classes.get(year_class) is None:
            continue

        first_year = year_classes[year_class].first_year
        last_year = year_classes[year_class].last_year
        last_year_ext = None if year_classes.get(year_class_ext) is None else year_classes[year_class_ext].last_year

        items[code] = BuildingType(
            code,
            country,
            region,
            building_size_class,
            building_size_class_ext,
            year_class,
            year_class_ext,
            first_year,
            last_year,
            last_year_ext,
        )
        rows.append(
            [
                None,
                code,
                country,
                region,
                building_size_class,
                building_size_class_ext,
                0.0,
                year_class,
                year_class_ext,
                first_year,
                last_year,
                last_year_ext,
                "Residential building",
                "TABULA",
            ]
        )

    return BuildingTypeTransform(
        items=items,
        batch=TableBatch(
            table_name=TABULA_BUILDING_TYPE,
            create_sql=BUILDING_TYPE_CREATE_SQL,
            insert_sql=f"insert into {TABULA_BUILDING_TYPE} values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows=rows,
            error_message="building type table error",
        ),
    )


def transform_buildings(
    table,
    year_classes: dict[str, YearClass],
    building_types: dict[str, BuildingType],
) -> BuildingTransform:
    items: dict[str, Building] = {}
    rows: list[list[object]] = []

    for index in range(len(table)):
        if index < 14:
            continue

        code = table.at[index, "Code_Building"]
        country = table.at[index, "Code_Country"]
        building_type_code = table.at[index, "Code_BuildingType"]
        data_type = table.at[index, "Code_DataType_Building"]

        if building_types.get(building_type_code) is None:
            continue

        description = table.at[index, "Description_Building"]
        year_class = building_types[building_type_code].year_class
        first_year = year_classes[year_class].first_year
        last_year = year_classes[year_class].last_year
        year_class_ext = building_types[building_type_code].year_class_ext
        last_year_ext = None if year_class_ext is None or year_classes.get(year_class_ext) is None else year_classes[year_class_ext].last_year

        roof_1 = table.at[index, "Code_Roof_1"]
        roof_2 = table.at[index, "Code_Roof_2"]
        wall_1 = table.at[index, "Code_Wall_1"]
        wall_2 = table.at[index, "Code_Wall_2"]
        wall_3 = table.at[index, "Code_Wall_3"]
        floor_1 = table.at[index, "Code_Floor_1"]
        floor_2 = table.at[index, "Code_Floor_2"]
        window_1 = table.at[index, "Code_Window_1"]
        window_2 = table.at[index, "Code_Window_2"]
        door_1 = table.at[index, "Code_Door_1"]
        ref_area = rounded_down_to_2_decimals(table.at[index, "A_C_Ref"])

        items[code] = Building(
            code,
            country,
            building_type_code,
            data_type,
            description,
            year_class,
            first_year,
            last_year,
            year_class_ext,
            last_year_ext,
            roof_1,
            roof_2,
            wall_1,
            wall_2,
            wall_3,
            floor_1,
            floor_2,
            window_1,
            window_2,
            door_1,
            ref_area,
        )
        building_types[building_type_code].areas.append(ref_area)

        rows.append(
            [
                None,
                code,
                building_type_code,
                data_type,
                description,
                ref_area,
                roof_1,
                roof_2,
                wall_1,
                wall_2,
                wall_3,
                floor_1,
                floor_2,
                window_1,
                window_2,
                door_1,
            ]
        )

    return BuildingTransform(
        items=items,
        batch=TableBatch(
            table_name=TABULA_BUILDING,
            create_sql=BUILDING_CREATE_SQL,
            insert_sql=f"insert into {TABULA_BUILDING} values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows=rows,
            error_message="table building error",
        ),
    )


def apply_average_area_updates(cursor, building_types: dict[str, BuildingType]) -> None:
    for code, building_type in building_types.items():
        if not building_type.areas:
            continue

        mean_area = rounded_down_to_2_decimals(statistics.fmean(building_type.areas))
        safe_execute(
            cursor,
            f"UPDATE {TABULA_BUILDING_TYPE} SET average_area = ? WHERE code = ?",
            [mean_area, code],
            error_message="tabula building type average area update error",
                    )


def transform_constructions(table) -> ConstructionTransform:
    items: dict[str, Construction] = {}
    rows: list[list[object]] = []

    for index in range(len(table)):
        if index < 10:
            continue

        country = table.at[index, "Code_Country"]
        if country == "XX":
            continue

        code = table.at[index, "Code_Construction"]
        variant = table.at[index, "Number_Construction_Variant"]
        element = table.at[index, "Code_ElementType"]
        name = table.at[index, "Type_Construction"]
        name_national = table.at[index, "Type_Construction_National"]
        description = table.at[index, "Description_Construction"]
        description_national = table.at[index, "Description_Construction_National"]
        first_year = table.at[index, "Year1_Construction"]
        last_year = table.at[index, "Year2_Construction"]
        u_value = table.at[index, "U"]
        d_insulation = table.at[index, "d_Insulation"]
        g_value = table.at[index, "g_gl_n"]

        items[code] = Construction(
            code,
            country,
            variant,
            element,
            first_year,
            last_year,
            name,
            name_national,
            description,
            description_national,
            u_value,
            d_insulation,
            g_value,
        )
        rows.append(
            [
                None,
                code,
                country,
                variant,
                element,
                name,
                name_national,
                description,
                description_national,
                first_year,
                last_year,
                u_value,
                d_insulation,
                g_value,
            ]
        )

    return ConstructionTransform(
        items=items,
        batch=TableBatch(
            table_name=TABULA_CONSTRUCTION,
            create_sql=CONSTRUCTION_CREATE_SQL,
            insert_sql=f"insert into {TABULA_CONSTRUCTION} values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows=rows,
            error_message="Construction table error",
        ),
    )


def main() -> None:
    source_tables = extract_source_tables()
    year_class_result = transform_year_classes(source_tables.year_classes)
    building_type_result = transform_building_types(source_tables.building_types, year_class_result.items)
    location_batch = transform_locations(source_tables.locations)
    building_result = transform_buildings(source_tables.buildings, year_class_result.items, building_type_result.items)
    construction_result = transform_constructions(source_tables.constructions)

    with connect(MAIN_DB_PATH) as conn:
        cursor = conn.cursor()
        write_table_batch(cursor, year_class_result.batch)
        write_table_batch(cursor, building_type_result.batch)
        write_table_batch(cursor, location_batch)
        write_table_batch(cursor, building_result.batch)
        apply_average_area_updates(cursor, building_type_result.items)
        write_table_batch(cursor, construction_result.batch)
        conn.commit()


if __name__ == "__main__":
    main()
