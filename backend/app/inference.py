import re
from collections.abc import Iterable

import pandas as pd

COLUMN_TYPES = ("date", "tenor", "currency", "rate", "product", "ignore")

_HEADER_TERMS = {
    "date": ("date", "as of", "effective", "priced", "pricing", "updated"),
    "tenor": ("tenor", "term", "maturity", "fixed period", "duration"),
    "currency": ("currency", "ccy", "denomination", "curr"),
    "rate": ("rate", "yield", "apr", "interest", "coupon"),
    "product": ("product", "offering", "facility", "plan", "name"),
    "ignore": ("note", "comment", "source", "description", "minimum", "maximum"),
}

_TENOR_PATTERN = re.compile(
    r"^\s*(?:\d+(?:\.\d+)?\s*(?:d|day|days|w|week|weeks|m|mo|month|months|y|yr|year|years)|"
    r"\d+\s*(?:m|y))\s*$",
    re.IGNORECASE,
)
_DATE_PATTERN = re.compile(
    r"^\s*(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s*$"
)
_CURRENCY_CODES = {
    "AUD", "CAD", "CHF", "CNY", "DKK", "EUR", "GBP", "HKD", "INR", "JPY",
    "NOK", "NZD", "SEK", "SGD", "USD", "ZAR",
}


def _values(series: pd.Series) -> list[str]:
    return [str(value).strip() for value in series.dropna().tolist() if str(value).strip()]


def _header_scores(header: object) -> dict[str, float]:
    normalized = re.sub(r"[_\-]+", " ", str(header).strip().lower())
    normalized = re.sub(r"\s+", " ", normalized)
    scores = {column_type: 0.0 for column_type in COLUMN_TYPES}

    for column_type, terms in _HEADER_TERMS.items():
        for term in terms:
            if normalized == term:
                scores[column_type] = 0.94
                break
            if term in normalized:
                scores[column_type] = max(scores[column_type], 0.82)

    return scores


def find_header_row(raw_frame: pd.DataFrame, scan_limit: int = 30) -> int | None:
    """Locate a likely ratesheet header row in a table with optional preamble rows."""
    best_row: int | None = None
    best_score = 0

    for row_index, row in raw_frame.head(scan_limit).iterrows():
        recognized: set[str] = set()
        for value in row.tolist():
            scores = _header_scores(value)
            column_type = max(scores, key=scores.get)
            if column_type != "ignore" and scores[column_type] >= 0.7:
                recognized.add(column_type)

        score = len(recognized)
        if "rate" in recognized and score >= 2 and score > best_score:
            best_row = int(row_index)
            best_score = score

    return best_row


def _value_scores(values: Iterable[str]) -> dict[str, float]:
    sample = list(values)
    if not sample:
        return {column_type: 0.0 for column_type in COLUMN_TYPES}

    count = len(sample)
    tenor_ratio = sum(bool(_TENOR_PATTERN.match(value)) for value in sample) / count
    date_ratio = sum(bool(_DATE_PATTERN.match(value)) for value in sample) / count
    currency_ratio = sum(value.upper() in _CURRENCY_CODES for value in sample) / count

    numeric_values = pd.to_numeric(pd.Series(sample).str.replace("%", "", regex=False), errors="coerce")
    numeric_ratio = float(numeric_values.notna().mean())
    rates_in_range = numeric_values.dropna().between(0, 100).mean() if numeric_values.notna().any() else 0.0
    product_ratio = sum(not bool(re.fullmatch(r"[\d.,%+\-\s]+", value)) for value in sample) / count

    return {
        "date": date_ratio * 0.86,
        "tenor": tenor_ratio * 0.9,
        "currency": currency_ratio * 0.92,
        "rate": numeric_ratio * (0.35 + 0.45 * float(rates_in_range)),
        "product": product_ratio * 0.38,
        "ignore": 0.0,
    }


def infer_columns(frame: pd.DataFrame) -> list[dict[str, str | float]]:
    """Infer a supported semantic type and confidence for every dataframe column.

    Header names are the strongest signal. Sample values provide a fallback for
    unusual or missing labels, with conservative confidence for ambiguous data.
    """
    inferred: list[dict[str, str | float]] = []

    for column in frame.columns:
        header_scores = _header_scores(column)
        value_scores = _value_scores(_values(frame[column]))
        candidates = {
            column_type: max(header_scores[column_type], value_scores[column_type])
            for column_type in COLUMN_TYPES
        }
        column_type = max(COLUMN_TYPES, key=lambda candidate: candidates[candidate])
        confidence = candidates[column_type]

        # Generic numeric fields are more likely to be a rate than a product,
        # while unlabeled, mixed text fields remain explicitly low confidence.
        if confidence < 0.3:
            column_type = "ignore"
            confidence = 0.25 if _values(frame[column]) else 0.1

        inferred.append(
            {
                "column": str(column),
                "type": column_type,
                "confidence": round(float(min(confidence, 0.99)), 2),
            }
        )

    return inferred
