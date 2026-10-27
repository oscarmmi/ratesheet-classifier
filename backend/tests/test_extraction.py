from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.extraction import extract_rates
from app.inference import infer_columns

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "samples"


@pytest.mark.parametrize(
    ("sample_name", "loader", "expected_rows"),
    [
        ("clean-rates.csv", lambda path: pd.read_csv(path), 4),
        ("shifted-headers.xlsx", lambda path: pd.read_excel(path, header=2), 3),
    ],
)
def test_extracts_normalized_records_from_single_sheet_samples(
    sample_name: str, loader, expected_rows: int
) -> None:
    frame = loader(SAMPLES / sample_name)
    records = extract_rates(frame, infer_columns(frame))

    assert len(records) == expected_rows
    assert set(records[0]) == {"product", "tenor", "currency", "rate", "as_of"}
    assert records[0]["product"]
    assert records[0]["tenor"]
    assert records[0]["currency"]
    assert isinstance(records[0]["rate"], float)
    assert records[0]["as_of"]


def test_extracts_rate_records_from_each_data_sheet_in_mixed_workbook() -> None:
    sheets = pd.read_excel(SAMPLES / "mixed-sheets.xlsx", sheet_name=None)
    records = [
        record
        for frame in sheets.values()
        if any(item["type"] == "rate" for item in infer_columns(frame))
        for record in extract_rates(frame, infer_columns(frame))
    ]

    assert len(records) == 6
    assert {record["currency"] for record in records} == {"CAD", "USD", "EUR"}
    assert all(record["as_of"] == "2025-02-10" for record in records)
