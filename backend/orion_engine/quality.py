"""Data quality checks + quality score."""
from __future__ import annotations
import pandas as pd
import numpy as np
from .dtypes import classify_columns


def _iqr_outlier_count(s: pd.Series) -> int:
    try:
        x = s.dropna()
        if len(x) < 8:
            return 0
        q1, q3 = x.quantile(0.25), x.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0 or pd.isna(iqr):
            return 0
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        return int(((x < lo) | (x > hi)).sum())
    except Exception:
        return 0


def quality_report(df: pd.DataFrame) -> dict:
    n, m = df.shape
    roles = classify_columns(df)
    issues: list[dict] = []
    col_reports: dict[str, dict] = {}

    dup_rows = int(df.duplicated().sum())
    if dup_rows > 0:
        issues.append({
            "id": "duplicate_rows", "severity": "medium" if dup_rows / max(n, 1) < 0.05 else "high",
            "title": f"{dup_rows:,} duplicate row(s) detected",
            "detail": f"{dup_rows:,} of {n:,} rows ({100*dup_rows/max(n,1):.1f}%) are exact duplicates. Duplicates can bias aggregates and leak between train/test splits.",
            "columns": [], "actions": ["remove_duplicates"],
        })

    for col in df.columns:
        s = df[col]
        role = roles.get(col, "text")
        missing = int(s.isna().sum())
        miss_pct = 100 * missing / n if n else 0
        nunique = int(s.nunique(dropna=True))
        rep: dict = {"role": role, "missing": missing, "missing_pct": round(miss_pct, 2),
                     "unique": nunique, "dtype": str(s.dtype), "flags": []}
        # empty column
        if missing == n:
            rep["flags"].append("empty_column")
            issues.append({"id": f"empty:{col}", "severity": "high", "title": f"'{col}' is completely empty",
                           "detail": f"'{col}' contains 100% missing values. It carries no information and is usually safe to drop.",
                           "columns": [col], "actions": ["drop_column"]})
        elif miss_pct >= 40:
            rep["flags"].append("excessive_missing")
            issues.append({"id": f"excessive_missing:{col}", "severity": "high",
                           "title": f"'{col}' has {miss_pct:.1f}% missing values",
                           "detail": f"'{col}' contains {miss_pct:.1f}% missing values. Consider dropping the column, or imputing only if the missingness mechanism is understood.",
                           "columns": [col], "actions": ["fill_median", "fill_mode", "drop_column", "drop_rows"]})
        elif miss_pct >= 5:
            rep["flags"].append("missing")
            issues.append({"id": f"missing:{col}", "severity": "medium" if miss_pct < 20 else "high",
                           "title": f"'{col}' has {miss_pct:.1f}% missing values",
                           "detail": f"'{col}' contains {missing:,} missing value(s) ({miss_pct:.1f}%). Choose an imputation strategy appropriate to the column type.",
                           "columns": [col], "actions": ["fill_mean", "fill_median", "fill_mode", "ffill", "bfill", "drop_rows"]})
        elif missing > 0:
            rep["flags"].append("missing_small")
            issues.append({"id": f"missing_small:{col}", "severity": "low",
                           "title": f"'{col}' has {missing} missing value(s) ({miss_pct:.1f}%)",
                           "detail": f"A small amount of missing data in '{col}'. Median/mode imputation or dropping those rows are both reasonable.",
                           "columns": [col], "actions": ["fill_median", "fill_mode", "drop_rows"]})
        # constant column
        if nunique <= 1 and missing < n:
            rep["flags"].append("constant")
            issues.append({"id": f"constant:{col}", "severity": "medium",
                           "title": f"'{col}' is constant",
                           "detail": f"'{col}' has only one distinct value. It cannot explain variation in any target and is usually dropped before modelling.",
                           "columns": [col], "actions": ["drop_column"]})
        # high cardinality categorical
        if role == "categorical" and nunique > 50 and nunique / max(n, 1) > 0.1 and n > 0:
            rep["flags"].append("high_cardinality")
            issues.append({"id": f"highcard:{col}", "severity": "medium",
                           "title": f"'{col}' has high cardinality ({nunique} distinct values)",
                           "detail": f"'{col}' has {nunique} distinct values. One-hot encoding would explode features; consider grouping rare categories, target encoding, or treating it as an identifier.",
                           "columns": [col], "actions": ["drop_column"]})
        # outliers numeric
        if role == "numeric":
            k = _iqr_outlier_count(s)
            rep["outliers_iqr"] = k
            if k > 0 and k / max(n, 1) >= 0.01:
                rep["flags"].append("outliers")
                issues.append({"id": f"outliers:{col}", "severity": "low" if k / max(n, 1) < 0.05 else "medium",
                               "title": f"'{col}' has ~{k} potential outlier(s) (IQR rule)",
                               "detail": f"About {k} value(s) in '{col}' fall outside 1.5×IQR. Outliers may be errors or genuine extremes — inspect before capping or removing.",
                               "columns": [col], "actions": ["cap_outliers", "drop_outliers"]})
        # whitespace / inconsistent text
        if role in ("categorical", "text"):
            try:
                strvals = s.dropna().astype(str)
                if len(strvals):
                    lead_trail = int((strvals != strvals.str.strip()).sum())
                    if lead_trail > 0:
                        rep["flags"].append("whitespace")
                        issues.append({"id": f"whitespace:{col}", "severity": "low",
                                       "title": f"'{col}' has {lead_trail} value(s) with leading/trailing whitespace",
                                       "detail": f"Extra spaces create phantom categories (e.g. 'Male' vs ' Male'). Trimming whitespace is safe and recommended.",
                                       "columns": [col], "actions": ["trim_whitespace"]})
                    # case inconsistency: same value different case
                    lowered = strvals.str.strip().str.lower()
                    if strvals.str.strip().nunique() > lowered.nunique():
                        rep["flags"].append("case_inconsistent")
                        issues.append({"id": f"case:{col}", "severity": "low",
                                       "title": f"'{col}' has inconsistent capitalization",
                                       "detail": f"'{col}' contains values that differ only by case. Standardizing case merges these duplicates.",
                                       "columns": [col], "actions": ["standardize_case"]})
            except Exception:
                pass
        # mixed types in object columns
        if s.dtype == object:
            try:
                types = s.dropna().map(lambda x: type(x).__name__).value_counts()
                if len(types) > 1:
                    rep["flags"].append("mixed_types")
                    issues.append({"id": f"mixed:{col}", "severity": "medium",
                                   "title": f"'{col}' has mixed data types ({', '.join(types.index[:3])})",
                                   "detail": f"'{col}' mixes types ({', '.join(f'{k}: {v}' for k, v in types.items())}). Convert to a single dtype before analysis.",
                                   "columns": [col], "actions": ["convert_dtype"]})
            except Exception:
                pass
        # invalid dates: datetime col with NaT introduced? detect via object parse fails
        if role == "datetime":
            nat = int(s.isna().sum())
            # already counted as missing; add invalid date note only if many
            pass
        col_reports[col] = rep

    # invalid dates check for object cols that look like dates but failed? (lightweight)
    # quality score: start 100, subtract penalties
    score = 100.0
    total_cells = n * m if n and m else 0
    miss_cells = int(df.isna().sum().sum())
    if total_cells:
        score -= min(35, 100 * miss_cells / total_cells * 1.2)
    if n:
        score -= min(15, 100 * dup_rows / n * 2)
    # penalties per flag
    for c, r in col_reports.items():
        if "empty_column" in r["flags"]:
            score -= 5
        if "constant" in r["flags"]:
            score -= 3
        if "excessive_missing" in r["flags"]:
            score -= 4
        if "mixed_types" in r["flags"]:
            score -= 2
        if "outliers" in r["flags"]:
            score -= 1
    score = max(5, min(100, round(score, 1)))

    # order issues by severity
    order = {"high": 0, "medium": 1, "low": 2}
    issues.sort(key=lambda x: (order.get(x["severity"], 3), x["title"]))

    counts = {"high": sum(1 for i in issues if i["severity"] == "high"),
              "medium": sum(1 for i in issues if i["severity"] == "medium"),
              "low": sum(1 for i in issues if i["severity"] == "low")}
    return {"score": score, "counts": counts, "issues": issues[:120], "total_issues": len(issues),
            "columns": col_reports, "duplicate_rows": dup_rows}
