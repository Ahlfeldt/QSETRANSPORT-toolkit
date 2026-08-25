"""Canonical identifier handling shared by GRID and TTMATRIX adapters."""
from __future__ import annotations

import re
from typing import Any

import pandas as pd


def canonical_id(value: Any) -> str:
    """Convert common CSV representations to one stable location identifier."""
    text = str(value).strip()
    text = re.sub(r"^(cell_id|location_id)[_ ]?", "", text, flags=re.IGNORECASE)
    if re.fullmatch(r"[-+]?\d+\.0+", text):
        text = text.split(".", 1)[0]
    if text == "" or text.lower() in {"nan", "none"}:
        raise ValueError(f"Invalid location identifier: {value!r}")
    return text


def canonical_series(values: pd.Series) -> pd.Series:
    return values.map(canonical_id).astype("string")
