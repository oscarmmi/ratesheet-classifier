from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "samples"
client = TestClient(app)


def test_extract_accepts_csv_and_returns_inferred_mapping_and_rows() -> None:
    with (SAMPLES / "clean-rates.csv").open("rb") as sample:
        response = client.post("/extract", files={"file": ("clean-rates.csv", sample, "text/csv")})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_rows"] == 4
    assert payload["sheets"][0]["mapping"][3]["type"] == "rate"
    assert payload["sheets"][0]["rows"][0] == {
        "product": "Prime Saver",
        "tenor": "30 days",
        "currency": "USD",
        "rate": 4.25,
        "as_of": "2025-01-15",
    }


def test_extract_handles_mixed_sheet_workbook_and_mapping_override() -> None:
    with (SAMPLES / "mixed-sheets.xlsx").open("rb") as sample:
        response = client.post(
            "/extract",
            files={"file": ("mixed-sheets.xlsx", sample, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"mapping": '{"sheets":{"Term deposits":{"Product name":"ignore"}}}'},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_rows"] == 6
    assert {sheet["name"] for sheet in payload["sheets"]} == {"Term deposits", "Lending"}
    assert payload["sheets"][0]["rows"][0]["product"] is None
    assert payload["sheets"][1]["rows"][0]["product"] == "Home Flex"


def test_extract_returns_422_json_for_unreadable_and_unsupported_files() -> None:
    unreadable = client.post("/extract", files={"file": ("broken.xlsx", b"not an excel workbook")})
    unsupported = client.post("/extract", files={"file": ("rates.json", b"{}")})

    assert unreadable.status_code == 422
    assert isinstance(unreadable.json()["detail"], str)
    assert unsupported.status_code == 422
    assert isinstance(unsupported.json()["detail"], str)


def test_extract_rejects_files_over_five_megabytes() -> None:
    oversized = client.post("/extract", files={"file": ("large.csv", b"x" * (5 * 1024 * 1024 + 1))})

    assert oversized.status_code == 422
    assert "5 MB" in oversized.json()["detail"]
