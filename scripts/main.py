from __future__ import annotations

import os
from datetime import datetime

from core.builder_config import MAIN_DB_PATH
from core.dataSources import DATA_SOURCE
from core.db_utils import TableBatch, connect, write_table_batch


TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {DATA_SOURCE} (
    id integer primary key,
    name varchar,
    description varchar,
    url varchar,
    data_entry varchar,
    version varchar
)
"""

DATA_SOURCES = [
    ("Nais DB", "", "https://nais.tech/", None, "1.4"),
    ("TABULA", "", "https://episcope.eu/building-typology/tabula-webtool/", "2017-06-01", ""),
    ("IWU-NWG", "", "https://www.iwu.de/forschung/energie/vergleichswerte-energieverbrauch-nwg/", "2023-11-24", "2.2"),
    ("ALTBAU_ATLAS", "", "https://www.altbauatlas.de/", "", ""),
    ("EPD", "", "https://ibu-epd.com/veroeffentlichte-epds/", "", ""),
    ("CRREM", "", "https://crrem.org/crrem-pathways/", "2025-08-28", "2.04"),
]


def extract_build_date() -> str:
    return os.environ.get("NAIS_BUILD_DATE", datetime.today().strftime("%Y-%m-%d"))


def transform_data_source_rows(build_date: str) -> list[list[object]]:
    return [
        [None, name, description, url, build_date if data_entry is None else data_entry, version]
        for name, description, url, data_entry, version in DATA_SOURCES
    ]


def build_table_batch(rows: list[list[object]]) -> TableBatch:
    return TableBatch(
        table_name=DATA_SOURCE,
        create_sql=TABLE_SQL,
        insert_sql=f"INSERT INTO {DATA_SOURCE} VALUES (?, ?, ?, ?, ?, ?)",
        rows=rows,
        error_message="data source table insert error",
    )


def main() -> None:
    batch = build_table_batch(transform_data_source_rows(extract_build_date()))

    with connect(MAIN_DB_PATH) as conn:
        cursor = conn.cursor()
        write_table_batch(cursor, batch)
        conn.commit()


if __name__ == "__main__":
    main()
