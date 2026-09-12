"""File loading with robust encoding handling and validation."""
from __future__ import annotations
import io
import pandas as pd
from .dtypes import classify_columns, coerce_datetime_columns

MAX_ROWS_HARD = 1_000_000
MAX_COLS_HARD = 500
MAX_BYTES = 250 * 1024 * 1024  # 250MB guard


class LoadError(Exception):
    pass


def _try_read_csv(content: bytes) -> pd.DataFrame:
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]
    last_err = None
    for enc in encodings:
        try:
            text = content.decode(enc)
            if not text.strip():
                raise LoadError("The file appears to be empty.")
            # Parse two ways: default comma vs delimiter-sniffed; keep the better one.
            # (Sniffing alone mangles single-column files; comma alone misses ; or tab files.)
            df_comma, df_sniff = None, None
            try:
                df_comma = pd.read_csv(io.StringIO(text))
            except Exception as e:
                last_err = e
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    df_sniff = pd.read_csv(io.StringIO(text), sep=None, engine="python")
            except Exception as e:
                last_err = e
            df = None
            if df_comma is not None and df_sniff is not None:
                # Prefer sniffed only if it yields strictly more *named* columns
                def named(d):
                    return sum(1 for c in d.columns if not str(c).startswith("Unnamed"))
                if df_sniff.shape[1] > df_comma.shape[1] and named(df_sniff) >= named(df_comma):
                    df = df_sniff
                else:
                    df = df_comma
            else:
                df = df_comma if df_comma is not None else df_sniff
            if df is None:
                continue
            return df
        except LoadError:
            raise
        except Exception as e:
            last_err = e
            continue
    raise LoadError(f"Could not parse CSV with common encodings. Last error: {last_err}")


def load_table(filename: str, content: bytes) -> tuple[pd.DataFrame, str]:
    if len(content) == 0:
        raise LoadError("The uploaded file is empty (0 bytes).")
    if len(content) > MAX_BYTES:
        raise LoadError(f"File is too large ({len(content)/1024/1024:.1f} MB). Limit is {MAX_BYTES/1024/1024:.0f} MB.")
    lower = filename.lower()
    if lower.endswith(".csv"):
        df = _try_read_csv(content)
        ftype = "csv"
    elif lower.endswith(".xlsx") or lower.endswith(".xlsm"):
        try:
            df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
        except Exception as e:
            raise LoadError(f"Could not read Excel file (.xlsx): {e}")
        ftype = "excel"
    elif lower.endswith(".xls"):
        try:
            df = pd.read_excel(io.BytesIO(content), engine="xlrd")
        except Exception as e:
            raise LoadError(f"Could not read legacy Excel file (.xls): {e}")
        ftype = "excel"
    else:
        raise LoadError("Unsupported file type. Please upload a .csv, .xlsx or .xls file.")

    if df is None or df.shape[1] == 0:
        raise LoadError("No columns were detected in this file.")
    # Drop fully-empty rows/cols that Excel often adds? Keep cols for quality detection but drop all-NA rows beyond?
    # Keep as-is for honest quality reporting, except strip unnamed all-na columns beyond data? Keep.
    if df.shape[0] == 0:
        raise LoadError("The file has headers but no data rows.")
    if df.shape[0] > MAX_ROWS_HARD:
        raise LoadError(f"Dataset has {df.shape[0]:,} rows which exceeds the {MAX_ROWS_HARD:,} row safety limit.")
    if df.shape[1] > MAX_COLS_HARD:
        raise LoadError(f"Dataset has {df.shape[1]} columns which exceeds the {MAX_COLS_HARD} column safety limit.")

    # normalize column names: strip, dedupe
    cols = []
    seen: dict[str, int] = {}
    for i, c in enumerate(df.columns):
        name = str(c).strip() if str(c).strip() != "" else f"column_{i+1}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        cols.append(name)
    df.columns = cols

    # coerce datetime-like columns
    roles = classify_columns(df)
    df = coerce_datetime_columns(df, roles)
    return df, ftype


def memory_estimate(df: pd.DataFrame) -> int:
    try:
        return int(df.memory_usage(deep=True, index=True).sum())
    except Exception:
        return 0
