"""Dataset profiling: summary + per-column explorer."""
from __future__ import annotations
import math
import pandas as pd
import numpy as np
from .dtypes import classify_columns
from .loader import memory_estimate


def _safe(v):
    try:
        if v is None:
            return None
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        if isinstance(v, (np.floating,)):
            f = float(v)
            return None if (math.isnan(f) or math.isinf(f)) else f
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (pd.Timestamp,)):
            return v.isoformat()
        if hasattr(v, "isoformat"):
            try:
                return v.isoformat()
            except Exception:
                return str(v)
        if isinstance(v, (np.bool_, bool)):
            return bool(v)
        return v
    except Exception:
        return str(v)


def dataset_summary(df: pd.DataFrame, filename: str, filetype: str) -> dict:
    roles = classify_columns(df)
    numeric = [c for c, r in roles.items() if r == "numeric"]
    categorical = [c for c, r in roles.items() if r == "categorical"]
    dt = [c for c, r in roles.items() if r == "datetime"]
    boolean = [c for c, r in roles.items() if r == "boolean"]
    text = [c for c, r in roles.items() if r == "text"]
    missing_cells = int(df.isna().sum().sum())
    total_cells = int(df.shape[0] * df.shape[1]) if df.shape[0] and df.shape[1] else 0
    dup_rows = int(df.duplicated().sum())
    mem = memory_estimate(df)
    # dtypes
    dtypes = {c: str(df[c].dtype) for c in df.columns}
    return {
        "filename": filename,
        "filetype": filetype,
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "numeric_columns": numeric,
        "categorical_columns": categorical,
        "datetime_columns": dt,
        "boolean_columns": boolean,
        "text_columns": text,
        "roles": roles,
        "dtypes": dtypes,
        "missing_cells": missing_cells,
        "missing_pct": round(100 * missing_cells / total_cells, 2) if total_cells else 0,
        "duplicate_rows": dup_rows,
        "duplicate_pct": round(100 * dup_rows / len(df), 2) if len(df) else 0,
        "memory_bytes": mem,
        "memory_mb": round(mem / 1024 / 1024, 2),
    }


def column_profile(df: pd.DataFrame, col: str, roles: dict | None = None) -> dict:
    if col not in df.columns:
        raise ValueError(f"Column '{col}' not found")
    roles = roles or classify_columns(df)
    role = roles.get(col, "text")
    s = df[col]
    n = len(s)
    missing = int(s.isna().sum())
    nunique = int(s.nunique(dropna=True))
    out: dict = {
        "name": col,
        "role": role,
        "dtype": str(s.dtype),
        "count": int(s.notna().sum()),
        "missing": missing,
        "missing_pct": round(100 * missing / n, 2) if n else 0,
        "unique": nunique,
        "unique_pct": round(100 * nunique / n, 2) if n else 0,
    }
    if role == "numeric":
        desc = s.describe(percentiles=[0.25, 0.5, 0.75])
        out.update({
            "mean": _safe(float(s.mean()) if s.notna().any() else None),
            "median": _safe(float(s.median()) if s.notna().any() else None),
            "std": _safe(float(s.std()) if s.notna().sum() > 1 else None),
            "min": _safe(s.min()),
            "max": _safe(s.max()),
            "q1": _safe(float(desc.get("25%", float("nan")))),
            "q3": _safe(float(desc.get("75%", float("nan")))),
            "skew": _safe(float(s.skew()) if s.notna().sum() > 2 else None),
            "kurtosis": _safe(float(s.kurt()) if s.notna().sum() > 3 else None),
        })
    elif role == "datetime":
        try:
            out.update({
                "min": _safe(pd.to_datetime(s.min())) if s.notna().any() else None,
                "max": _safe(pd.to_datetime(s.max())) if s.notna().any() else None,
            })
        except Exception:
            pass
    # top values for categorical/text/boolean (and small-cardinality numeric too)
    try:
        vc = s.value_counts(dropna=True).head(10)
        out["top_values"] = [{"value": str(idx)[:120], "count": int(cnt), "pct": round(100 * cnt / n, 2) if n else 0} for idx, cnt in vc.items()]
        if len(vc):
            out["mode"] = str(vc.index[0])[:120]
            out["mode_count"] = int(vc.iloc[0])
    except Exception:
        out["top_values"] = []
    # sample values
    try:
        out["sample"] = [str(x)[:120] for x in s.dropna().head(5).tolist()]
    except Exception:
        out["sample"] = []
    return out


def full_profile(df: pd.DataFrame, max_columns: int = 200) -> dict:
    roles = classify_columns(df)
    cols = list(df.columns)[:max_columns]
    profiles = [column_profile(df, c, roles) for c in cols]
    return {"roles": roles, "columns": profiles, "truncated": len(df.columns) > max_columns}


def preview(df: pd.DataFrame, page: int = 1, page_size: int = 25, search: str = "", sort_col: str = "", sort_dir: str = "asc") -> dict:
    page = max(1, int(page))
    page_size = min(100, max(5, int(page_size)))
    work = df
    if search:
        q = search.strip().lower()
        if q:
            mask = None
            for c in work.columns:
                try:
                    m = work[c].astype(str).str.lower().str.contains(q, na=False)
                    mask = m if mask is None else (mask | m)
                except Exception:
                    continue
            if mask is not None:
                work = work[mask]
    total_filtered = int(work.shape[0])
    if sort_col and sort_col in work.columns:
        try:
            work = work.sort_values(by=sort_col, ascending=(sort_dir != "desc"), kind="mergesort")
        except Exception:
            pass
    total_pages = max(1, -(-total_filtered // page_size))
    page = min(page, total_pages)
    start = (page - 1) * page_size
    chunk = work.iloc[start:start + page_size]
    # stringify safely
    rows: list[dict] = []
    for _, r in chunk.iterrows():
        d: dict = {}
        for c in df.columns:
            v = r[c]
            if pd.isna(v):
                d[c] = None
            elif isinstance(v, (pd.Timestamp,)):
                d[c] = v.isoformat()
            elif isinstance(v, (np.floating, float)) and (math.isnan(float(v)) or math.isinf(float(v))):
                d[c] = None
            elif isinstance(v, (np.integer,)):
                d[c] = int(v)
            elif isinstance(v, (np.bool_,)):
                d[c] = bool(v)
            else:
                d[c] = v
        rows.append(d)
    # convert non-serializable leftovers
    import json
    clean_rows = json.loads(json.dumps(rows, default=str))
    return {
        "page": page, "page_size": page_size,
        "total_rows": int(df.shape[0]), "filtered_rows": total_filtered,
        "total_pages": total_pages,
        "columns": list(df.columns),
        "rows": clean_rows,
    }
