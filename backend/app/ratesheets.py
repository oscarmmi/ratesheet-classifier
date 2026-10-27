import csv
import io
from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from app.extraction import extract_rates
from app.inference import COLUMN_TYPES, find_header_row, infer_columns


def _unique_headers(values: Sequence[Any]) -> list[str]:
    headers: list[str] = []
    seen: dict[str, int] = {}
    for index, value in enumerate(values):
        name = str(value).strip() if pd.notna(value) else ""
        name = name or f"Column {index + 1}"
        count = seen.get(name, 0)
        seen[name] = count + 1
        headers.append(name if count == 0 else f"{name} ({count + 1})")
    return headers


def _frame_from_raw(raw: pd.DataFrame) -> tuple[int, pd.DataFrame] | None:
    header_row = find_header_row(raw)
    if header_row is None:
        return None

    headers = _unique_headers(raw.iloc[header_row].tolist())
    frame = raw.iloc[header_row + 1 :].copy().reset_index(drop=True)
    frame.columns = headers
    return header_row, frame.dropna(how="all")


def _csv_frames(content: bytes) -> dict[str, pd.DataFrame]:
    text = content.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    width = max((len(row) for row in rows), default=0)
    if width == 0:
        return {}
    raw = pd.DataFrame([row + [None] * (width - len(row)) for row in rows])
    parsed = _frame_from_raw(raw)
    return {"Rates": parsed[1]} if parsed else {}


def _excel_frames(content: bytes) -> dict[str, pd.DataFrame]:
    raw_sheets = pd.read_excel(io.BytesIO(content), sheet_name=None, header=None, engine="openpyxl")
    frames: dict[str, pd.DataFrame] = {}
    for name, raw in raw_sheets.items():
        parsed = _frame_from_raw(raw)
        if parsed:
            frames[str(name)] = parsed[1]
    return frames


def _apply_mapping_overrides(
    inferred: list[dict[str, str | float]], overrides: Mapping[str, str] | Sequence[Mapping[str, Any]] | None
) -> list[dict[str, str | float]]:
    if overrides is None:
        return inferred
    by_column = (
        dict(overrides)
        if isinstance(overrides, Mapping)
        else {
            str(item["column"]): str(item["type"])
            for item in overrides
            if "column" in item and "type" in item
        }
    )
    validated = {str(column): str(column_type) for column, column_type in by_column.items()}
    invalid = {column: column_type for column, column_type in validated.items() if column_type not in COLUMN_TYPES}
    if invalid:
        raise ValueError(f"Unsupported mapping type. Choose from: {', '.join(COLUMN_TYPES)}.")

    result = []
    for item in inferred:
        updated = dict(item)
        if updated["column"] in validated:
            updated["type"] = validated[updated["column"]]
            updated["confidence"] = 1.0
        result.append(updated)
    return result


def process_ratesheet(
    filename: str,
    content: bytes,
    overrides: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Parse a supported workbook, infer mappings, and return normalized rows."""
    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if extension not in {"csv", "xlsx"}:
        raise ValueError("Upload a .csv or .xlsx file.")
    if not content:
        raise ValueError("The uploaded file is empty.")

    try:
        frames = _csv_frames(content) if extension == "csv" else _excel_frames(content)
    except Exception as error:
        raise ValueError("The file could not be read. Check that it is a valid CSV or Excel workbook.") from error

    sheets = []
    for name, frame in frames.items():
        sheet_overrides = overrides
        if isinstance(overrides, Mapping) and "sheets" in overrides:
            sheet_overrides = overrides["sheets"].get(name, {})
        mapping = _apply_mapping_overrides(infer_columns(frame), sheet_overrides)
        if not any(item["type"] == "rate" for item in mapping):
            continue
        for item in mapping:
            values = frame[item["column"]].dropna()
            item["sample"] = str(values.iloc[0]) if not values.empty else ""
        sheets.append(
            {
                "name": name,
                "mapping": mapping,
                "rows": extract_rates(frame, mapping),
            }
        )

    if not sheets:
        raise ValueError("No rates table was found. Include a labeled rate column and at least one other recognized column.")

    return {
        "filename": filename,
        "sheets": sheets,
        "total_rows": sum(len(sheet["rows"]) for sheet in sheets),
    }
