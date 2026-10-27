# Ratesheet Classifier

A recruiter-facing data workbench that turns inconsistent lender spreadsheets into normalized rate records. It demonstrates a small, inspectable pipeline: read a workbook, infer likely column meanings, let a person review the mapping, and return clean JSON.

All included ratesheets contain fictional demo data. The application processes uploads in memory, does not persist files or rate data, and has no external bank integrations.

## Features

- Upload `.csv` and `.xlsx` files up to 5 MB.
- Detect header rows in workbooks with leading title or effective-date rows.
- Read multiple Excel sheets and skip sheets without a recognizable rate table.
- Infer column types with a confidence score and a sample value for review.
- Correct mappings per workbook sheet and re-run extraction.
- Return normalized rows with `product`, `tenor`, `currency`, `rate`, and `as_of` fields.
- Explore the FastAPI contract at `/docs`.

## Column mapping rules

Header words are the strongest signal. The classifier also checks representative cell values when a header is unfamiliar. Confidence is a review aid rather than a guarantee; the UI keeps every inferred type editable.

| Type | Typical header cues | Value cues |
| --- | --- | --- |
| `date` | date, as of, effective, pricing | Common numeric date formats |
| `tenor` | tenor, term, maturity, duration | Values such as `30 days`, `6 months`, `1 year`, or `2Y` |
| `currency` | currency, CCY, denomination | Common ISO currency codes such as `USD`, `EUR`, and `CAD` |
| `rate` | rate, yield, APR, interest, coupon | Numeric values, including values written with `%` |
| `product` | product, offering, facility, plan | Descriptive, non-numeric labels |
| `ignore` | notes and unrecognized columns | The safe fallback for low-confidence columns |

The output keeps percentage-point values as supplied (for example, `4.25` remains `4.25`, not `0.0425`). Dates in `as_of` are emitted as ISO `YYYY-MM-DD` strings, and currency codes are uppercase. If a field is not present in the source mapping, its normalized value is `null`.

## Requirements

- Python 3.10+
- Node.js 20+
- npm

## Run locally

From the repository root, create a virtual environment, install the API dependencies, and start FastAPI:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --app-dir backend
```

The health endpoint is <http://127.0.0.1:8000/api/health>. Interactive OpenAPI documentation is at <http://127.0.0.1:8000/docs>.

In a second terminal, install the frontend dependencies and start Vue + Vite:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite forwards `/extract` and `/api` requests to the local FastAPI server.

## API example

Extract the clean demo CSV with curl:

```bash
curl -X POST http://127.0.0.1:8000/extract \
  -F "file=@samples/clean-rates.csv"
```

An optional `mapping` form field is JSON. A simple object applies header overrides to every matching sheet:

```bash
curl -X POST http://127.0.0.1:8000/extract \
  -F "file=@samples/clean-rates.csv" \
  -F 'mapping={"Annual yield (%)":"rate"}'
```

For a workbook with different tables, apply overrides to one sheet at a time:

```json
{"sheets":{"Lending":{"Rate (%)":"rate"}}}
```

Invalid or unreadable input returns HTTP `422` with a JSON `detail` message.

## Demo ratesheets

The `samples/` directory contains three fictional inputs:

- `clean-rates.csv` — clearly labeled columns and four deposit rates.
- `shifted-headers.xlsx` — a title and effective-date preamble above the actual column headers.
- `mixed-sheets.xlsx` — separate term-deposit and lending tables plus a non-data notes sheet.

Regenerate the Excel workbooks with:

```bash
python scripts/generate_samples.py
```

## Tests and production build

```bash
python -m pytest backend/tests -q
cd frontend
npm run build
```

## Project structure

```text
backend/app/       FastAPI application, inference, parsing, and extraction
backend/tests/     Sample workbook and upload API tests
frontend/          Vue 3 + Vite + Tailwind CSS application
samples/           Fictional CSV and Excel inputs
scripts/           Demo sample generation utility
```
