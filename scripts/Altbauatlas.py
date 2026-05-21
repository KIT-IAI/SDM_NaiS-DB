from __future__ import annotations

import re
from dataclasses import dataclass

from models.AltbauatlasDB import AltBauConstruction
from core.builder_config import ALTBAUATLAS_SOURCE_DB_PATH, MAIN_DB_PATH
from core.dataSources import ALTBAU_ATLAS, ALTBAU_ATLAS_CONSTRUCTION, ALTBAU_ATLAS_MATERIAL
from core.db_utils import connect, drop_and_create_table, fetch_all


SOURCE_TABLE = "Altbauatlas"

MULTI_U_VALUE_MARKERS = [",", "-", "/", "k.A.", "X"]
YEAR_RANGE_RE = re.compile(r"(\d{4})?\s*bis\s*(\d{4})")

MATERIAL_CREATE_SQL = f"""CREATE TABLE IF NOT EXISTS {ALTBAU_ATLAS_MATERIAL} (
    id integer primary key,
    name varchar,
    postal_code varchar,
    first_year integer,
    last_year integer,
    strength real,
    raw_density real,
    lambda real,
    source_id varchar
)"""

CONSTRUCTION_CREATE_SQL = f"""CREATE TABLE IF NOT EXISTS {ALTBAU_ATLAS_CONSTRUCTION} (
    id integer primary key,
    name varchar,
    element_type varchar,
    materials varchar,
    postal_code varchar,
    first_year integer,
    last_year integer,
    materials_code varchar,
    u_value varchar,
    source_id varchar
)"""


@dataclass(frozen=True, slots=True)
class AltbauatlasExtract:
    origin_rows: list[tuple]
    materials_by_pdf: dict[str, list[dict[str, str]]]
    constructions: dict[str, AltBauConstruction]


def normalize_decimal_string(value: str) -> str:
    return value.replace(",", ".")


def parse_year_range(raw_value):
    first_year = 0o000
    last_year = 9999

    match = YEAR_RANGE_RE.match(raw_value)
    if match:
        first_year = match.group(1) if match.group(1) else "0000"
        last_year = match.group(2)

    return first_year, last_year


def has_multiple_u_values(u_values: str) -> bool:
    return any(separator in u_values for separator in MULTI_U_VALUE_MARKERS)


def extract_origin_rows() -> list[tuple]:
    return fetch_all(ALTBAUATLAS_SOURCE_DB_PATH, f"SELECT * FROM {SOURCE_TABLE}")


def transform_materials(origin_rows: list[tuple]) -> dict[str, list[dict[str, str]]]:
    materials: dict[str, list[dict[str, str]]] = {}
    for row in origin_rows:
        pdf_name = row[1]
        material_data = {
            "Material": row[7],
            "Staerke": normalize_decimal_string(row[8]),
            "Rohdichte": normalize_decimal_string(row[9]),
            "Lambda_Wert": normalize_decimal_string(row[10]),
        }
        materials.setdefault(pdf_name, []).append(material_data)
    return materials


def transform_constructions(
    origin_rows: list[tuple],
    materials_by_pdf: dict[str, list[dict[str, str]]],
) -> dict[str, AltBauConstruction]:
    constructions: dict[str, AltBauConstruction] = {}
    for row in origin_rows:
        pdf_name = row[1]
        postal_code = row[3]
        first_year, last_year = parse_year_range(row[4])
        element = row[5]
        name = row[6]
        u_value = normalize_decimal_string(row[11])

        constructions[pdf_name] = AltBauConstruction(
            pdf_name,
            name,
            element,
            materials_by_pdf[pdf_name],
            postal_code,
            first_year,
            last_year,
            u_value,
        )
    return constructions


def extract_dataset() -> AltbauatlasExtract:
    origin_rows = extract_origin_rows()
    materials_by_pdf = transform_materials(origin_rows)
    constructions = transform_constructions(origin_rows, materials_by_pdf)
    return AltbauatlasExtract(
        origin_rows=origin_rows,
        materials_by_pdf=materials_by_pdf,
        constructions=constructions,
    )


def prepare_target_tables(cursor) -> None:
    drop_and_create_table(cursor, ALTBAU_ATLAS_MATERIAL, MATERIAL_CREATE_SQL)
    cursor.execute(f"DROP TABLE IF EXISTS {ALTBAU_ATLAS}")
    drop_and_create_table(cursor, ALTBAU_ATLAS_CONSTRUCTION, CONSTRUCTION_CREATE_SQL)


def load_materials_and_constructions(cursor, constructions: dict[str, AltBauConstruction]) -> None:
    for construction in constructions.values():
        file_name = construction.file_name
        name = construction.name
        postal_code = construction.postal_code
        first_year = construction.first_year
        last_year = construction.last_year
        element = construction.element_type
        u_value = construction.u_value
        source_id = file_name.removeprefix("file_").removesuffix(".pdf")

        for material_item in construction.material:
            name = material_item["Material"]
            strength = material_item["Staerke"]
            raw_density = material_item["Rohdichte"]
            lambda_value = material_item["Lambda_Wert"]
            cursor.execute(
                f"INSERT INTO {ALTBAU_ATLAS_MATERIAL} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [None, name, postal_code, first_year, last_year, strength, raw_density, lambda_value, source_id],
            )

        if has_multiple_u_values(u_value):
            continue

        material_names = []
        material_refs = []
        cursor.execute(
            f"SELECT * FROM {ALTBAU_ATLAS_MATERIAL} WHERE source_id IS ?",
            [source_id],
        )
        material_rows = cursor.fetchall()

        for row in material_rows:
            material_refs.append(row[0])
            material_names.append(row[1])

        material_ref_string = str(material_refs).replace("[", "").replace("]", "")
        material_name_string = str(material_names).replace("[", "").replace("]", "").replace("'", "")

        cursor.execute(
            f"INSERT INTO {ALTBAU_ATLAS_CONSTRUCTION} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                None,
                name,
                element,
                material_name_string,
                postal_code,
                first_year,
                last_year,
                material_ref_string,
                u_value,
                source_id,
            ],
        )


def main() -> None:
    dataset = extract_dataset()

    with connect(MAIN_DB_PATH) as conn:
        cursor = conn.cursor()
        prepare_target_tables(cursor)
        load_materials_and_constructions(cursor, dataset.constructions)
        conn.commit()


if __name__ == "__main__":
    main()
