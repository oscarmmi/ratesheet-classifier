import json

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.inference import COLUMN_TYPES
from app.ratesheets import process_ratesheet

app = FastAPI(
    title="Ratesheet Classifier API",
    description="A demo API for turning messy ratesheets into structured rate data.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


@app.get("/api/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Return a lightweight readiness response for the local API."""
    return {"status": "ok", "service": "ratesheet-classifier-api"}


@app.post("/extract", tags=["ratesheets"])
async def extract_ratesheet(
    file: UploadFile = File(..., description="A CSV or XLSX ratesheet, up to 5 MB."),
    mapping: str | None = Form(
        default=None,
        description="Optional JSON object mapping column headers to one of the supported column types.",
    ),
) -> dict:
    """Infer a ratesheet mapping and return normalized rows for each data sheet."""
    filename = file.filename or ""
    if not filename.lower().endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=422, detail="Upload a .csv or .xlsx file.")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=422, detail="The file is larger than the 5 MB upload limit.")

    overrides = None
    if mapping:
        try:
            overrides = json.loads(mapping)
        except json.JSONDecodeError as error:
            raise HTTPException(status_code=422, detail="Mapping must be valid JSON.") from error
        if not isinstance(overrides, (dict, list)):
            raise HTTPException(status_code=422, detail="Mapping must be a JSON object or list of column mappings.")
        if isinstance(overrides, dict):
            if set(overrides) == {"sheets"}:
                sheet_mappings = overrides["sheets"]
                if not isinstance(sheet_mappings, dict) or not all(
                    isinstance(sheet_name, str)
                    and isinstance(sheet_mapping, dict)
                    and all(isinstance(column, str) and isinstance(column_type, str) for column, column_type in sheet_mapping.items())
                    for sheet_name, sheet_mapping in sheet_mappings.items()
                ):
                    raise HTTPException(status_code=422, detail="Per-sheet mappings must map sheet names to column/type objects.")
            elif not all(isinstance(value, str) for value in overrides.values()):
                raise HTTPException(status_code=422, detail="Each mapping value must be a column type.")
        if isinstance(overrides, list) and not all(
            isinstance(item, dict) and isinstance(item.get("column"), str) and isinstance(item.get("type"), str)
            for item in overrides
        ):
            raise HTTPException(status_code=422, detail="Each mapping item needs a column and type.")

    try:
        return process_ratesheet(filename, content, overrides)
    except ValueError as error:
        message = str(error)
        if "Unsupported mapping type" in message:
            message = f"{message} Supported types: {', '.join(COLUMN_TYPES)}."
        raise HTTPException(status_code=422, detail=message) from error
