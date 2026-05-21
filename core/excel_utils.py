from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pandas as pd


def read_excel_sheet(path, sheet_name: str) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet_name)


def iter_row_indices(table: pd.DataFrame, start_row: int) -> Iterator[int]:
    return iter(range(start_row, len(table)))


def build_rows(
    table: pd.DataFrame,
    start_row: int,
    row_builder: Callable[[pd.DataFrame, int], list[Any] | None],
) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for index in iter_row_indices(table, start_row):
        row = row_builder(table, index)
        if row is not None:
            rows.append(row)
    return rows
