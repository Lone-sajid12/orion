"""Column role detection: numeric / categorical / datetime / text."""
from __future__ import annotations
import warnings
import pandas as pd
import numpy as np


def classify_columns(df: pd.DataFrame) -> dict:
    """Return {col: role} where role in numeric|categorical|datetime|text|boolean."""
    roles: dict[str, str] = {}
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_bool_dtype(s):
            roles[col] = "boolean"
        elif pd.api.types.is_datetime64_any_dtype(s):
            roles[col] = "datetime"
        elif pd.api.types.is_numeric_dtype(s):
            # low-cardinality integer could still be numeric; keep numeric
            roles[col] = "numeric"
        else:
            # try datetime coercion for object columns (only if mostly parseable)
            roles[col] = _classify_object(s)
    return roles


def _classify_object(s: pd.Series) -> str:
    non_null = s.dropna()
    if len(non_null) == 0:
        return "text"
    # try datetime
    try:
        sample = non_null.sample(min(50, len(non_null)), random_state=0) if len(non_null) > 50 else non_null
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parsed = pd.to_datetime(sample, errors="coerce", format=None)
        if parsed.notna().mean() >= 0.0 and parsed.notna().sum() >= max(3, int(len(sample) * 0.7)) and len(sample) >= 3:
            # guard: pure numbers as strings should not become datetime
            if not _looks_like_plain_numbers(sample):
                return "datetime"
    except Exception:
        pass
    nunique = non_null.nunique(dropna=True)
    n = len(non_null)
    # high cardinality long text -> text, else categorical
    avg_len = 0
    try:
        avg_len = non_null.astype(str).str.len().mean()
    except Exception:
        avg_len = 0
    if nunique / max(n, 1) > 0.9 and (avg_len or 0) > 24:
        return "text"
    if nunique > 100 and nunique / max(n, 1) > 0.5:
        return "text"
    return "categorical"


def _looks_like_plain_numbers(sample: pd.Series) -> bool:
    try:
        as_str = sample.astype(str).str.strip()
        numeric_like = as_str.str.match(r"^-?\d+(\.\d+)?$").mean()
        return float(numeric_like) > 0.7
    except Exception:
        return False


def coerce_datetime_columns(df: pd.DataFrame, roles: dict) -> pd.DataFrame:
    """Best-effort: convert object columns classified as datetime to datetime64."""
    out = df.copy()
    for col, role in roles.items():
        if role == "datetime" and not pd.api.types.is_datetime64_any_dtype(out[col]):
            try:
                out[col] = pd.to_datetime(out[col], errors="coerce", format=None)
            except Exception:
                pass
    return out
