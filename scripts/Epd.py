from __future__ import annotations

from dataclasses import dataclass

from models.EPDDB import EpdMaterial
from core.builder_config import EPD_SOURCE_DB_PATH, MAIN_DB_PATH
from core.dataSources import EPD_MATERIAL
from core.db_utils import TableBatch, connect, fetch_all, write_table_batch


SOURCE_TABLE = "EPDs"
TEST_TABLE = EPD_MATERIAL + "_test "

MAIN_TABLE_CREATE_SQL = f"""CREATE TABLE IF NOT EXISTS {EPD_MATERIAL} (
    id integer primary key,
    source_file varchar,
    declaration_number varchar,
    product_name varchar,
    owner varchar,
    exhibition_year varchar,
    valid_until varchar,
    technical_data varchar
)"""

TEST_TABLE_CREATE_SQL = f"""CREATE TABLE IF NOT EXISTS {TEST_TABLE} (
    id integer primary key,
    source_file varchar,
    declaration_number varchar,
    product_name varchar,
    owner varchar,
    exhibition_year varchar,
    valid_until varchar,
    density varchar,
    raw_density varchar,
    thermal_conductivity varchar,
    technical_data varchar
)"""


@dataclass(frozen=True, slots=True)
class EpdExtract:
    origin_rows: list[tuple]
    material_fragments: dict[str, list[tuple]]
    epd_materials: dict[str, EpdMaterial]


def extract_origin_rows() -> list[tuple]:
    return fetch_all(EPD_SOURCE_DB_PATH, f"SELECT * FROM {SOURCE_TABLE}")


def transform_material_fragments(origin_rows: list[tuple]) -> dict[str, list[tuple]]:
    materials: dict[str, list[tuple]] = {}
    for row in origin_rows:
        declaration_number = row[1]
        material_data = (row[9], row[10], row[11])
        materials.setdefault(declaration_number, []).append(material_data)
    return materials


def transform_epd_materials(origin_rows: list[tuple], materials: dict[str, list[tuple]]) -> dict[str, EpdMaterial]:
    epd_materials: dict[str, EpdMaterial] = {}
    for row in origin_rows:
        declaration_number = row[1]
        product_unit = row[2]
        file_name = row[3]
        owner = row[4]
        version = row[5]
        exhibition = row[6]
        valid_until = row[7]

        density = "--"
        raw_density = "--"
        thermal_conductivity = "--"

        for material_name, part1_raw, part2_raw in materials[declaration_number]:
            name = material_name.strip().lower()
            part1 = str(part1_raw).strip()
            part2 = str(part2_raw).strip()

            if "rohdichte" in name or "raw density" in name or "gross density" in name:
                raw_density = part1 + " " + part2
            elif "dichte" in name or "density" in name:
                density = part1 + " " + part2

            if "wärmeleitfähigkeit" in name or "thermal conductivity" in name:
                thermal_conductivity = part1 + " " + part2

        technical_data = str(materials[declaration_number])
        epd_materials[declaration_number] = EpdMaterial(
            file_name,
            declaration_number,
            product_unit,
            owner,
            version,
            exhibition,
            valid_until,
            density,
            raw_density,
            thermal_conductivity,
            technical_data,
        )
    return epd_materials


def extract_dataset() -> EpdExtract:
    origin_rows = extract_origin_rows()
    material_fragments = transform_material_fragments(origin_rows)
    epd_materials = transform_epd_materials(origin_rows, material_fragments)
    return EpdExtract(
        origin_rows=origin_rows,
        material_fragments=material_fragments,
        epd_materials=epd_materials,
    )


def build_main_table_batch(epd_materials: dict[str, EpdMaterial]) -> TableBatch:
    rows = [
        [
            None,
            material.file_name,
            material.declaration_number,
            material.product_unit,
            material.owner,
            material.year_of_exhibition,
            material.valid_until,
            material.technical_data,
        ]
        for material in epd_materials.values()
    ]
    return TableBatch(
        table_name=EPD_MATERIAL,
        create_sql=MAIN_TABLE_CREATE_SQL,
        insert_sql=f"INSERT INTO {EPD_MATERIAL} VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows=rows,
        error_message="epd main table write error",
    )


def build_test_table_batch(epd_materials: dict[str, EpdMaterial]) -> TableBatch:
    rows = [
        [
            None,
            material.file_name,
            material.declaration_number,
            material.product_unit,
            material.owner,
            material.year_of_exhibition,
            material.valid_until,
            material.density,
            material.raw_density,
            material.thermal_conductivity,
            material.technical_data,
        ]
        for material in epd_materials.values()
    ]
    return TableBatch(
        table_name=TEST_TABLE,
        create_sql=TEST_TABLE_CREATE_SQL,
        insert_sql=f"INSERT INTO {TEST_TABLE} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows=rows,
        error_message="epd test table write error",
    )


def main() -> None:
    dataset = extract_dataset()
    batches = [
        build_main_table_batch(dataset.epd_materials),
        build_test_table_batch(dataset.epd_materials),
    ]

    with connect(MAIN_DB_PATH) as conn:
        cursor = conn.cursor()
        for batch in batches:
            write_table_batch(cursor, batch)
        conn.commit()


if __name__ == "__main__":
    main()
