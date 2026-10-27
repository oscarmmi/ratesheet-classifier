from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any

import pandas as pd

NORMALIZED_FIELDS = ("product", "tenor", "currency", "rate", "as_of")


def _mapping_by_column(
    mapping: Mapping[str, str] | Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    if isinstance(mapping, Mapping):
        return {str(column): str(column_type) for column, column_type in mapping.items()}

    return {
        str(item["column"]): str(item["type"])
        for item in mapping
        if "column" in item and "type" in item
    }


def _clean_text(value: Any) -> str | None:
    if pd.isna(value):
        return None
    text = " ".join(str(value).split())
    return text or None


def _clean_rate(value: Any) -> float | None:
    if pd.isna(value):
        return None
    if isinstance(value, str):
        normalized = value.strip().replace(",", "").replace("%", "")
        if normalized.startswith("(") and normalized.endswith(")"):
            normalized = f"-{normalized[1:-1]}"
        try:
            return float(normalized)
        except ValueError:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_date(value: Any) -> str | None:
    if pd.isna(value):
        return None
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    parsed = pd.to_datetime(str(value).strip(), errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date().isoformat()


def extract_rates(
    frame: pd.DataFrame,
    mapping: Mapping[str, str] | Sequence[Mapping[str, Any]],
) -> list[dict[str, str | float | None]]:
    """Convert a dataframe and its reviewed column mapping into rate records."""
    by_column = _mapping_by_column(mapping)
    source_columns = {
        field: next(
            (column for column, column_type in by_column.items() if column_type == field),
            None,
        )
        for field in ("product", "tenor", "currency", "rate")
    }
    source_columns["as_of"] = next(
        (column for column, column_type in by_column.items() if column_type == "date"),
        None,
    )

    records: list[dict[str, str | float | None]] = []
    for _, row in frame.iterrows():
        record: dict[str, str | float | None] = {}
        for field in NORMALIZED_FIELDS:
            column = source_columns[field]
            value = row[column] if column in frame.columns else None
            if field == "rate":
                record[field] = _clean_rate(value)
            elif field == "as_of":
                record[field] = _clean_date(value)
            else:
                cleaned = _clean_text(value)
                record[field] = cleaned.upper() if field == "currency" and cleaned else cleaned

        if any(value is not None for value in record.values()):
            records.append(record)

    return records
