"""Cleaning operations. Each op returns (new_df, code_string, summary)."""
from __future__ import annotations
import pandas as pd
import numpy as np


def _code_header() -> str:
    return "import pandas as pd\nimport numpy as np\n\n# df is your working DataFrame\n"


def apply_operation(df: pd.DataFrame, op: dict) -> tuple[pd.DataFrame, str, str]:
    name = op.get("op")
    if name == "remove_duplicates":
        before = len(df)
        out = df.drop_duplicates().reset_index(drop=True)
        removed = before - len(out)
        code = _code_header() + f"before = len(df)\ndf = df.drop_duplicates().reset_index(drop=True)\nprint(f\"Removed {{before - len(df)}} duplicate rows\")\n"
        return out, code, f"Removed {removed:,} duplicate row(s)."
    if name == "drop_column":
        cols = op.get("columns", [])
        if isinstance(cols, str):
            cols = [cols]
        cols = [c for c in cols if c in df.columns]
        if not cols:
            raise ValueError("No valid columns selected to drop.")
        out = df.drop(columns=cols)
        code = _code_header() + f"df = df.drop(columns={cols!r})\n"
        return out, code, f"Dropped column(s): {', '.join(cols)}."
    if name == "drop_rows_missing":
        cols = op.get("columns") or []
        if isinstance(cols, str):
            cols = [cols]
        subset = [c for c in cols if c in df.columns] or None
        before = len(df)
        out = df.dropna(subset=subset).reset_index(drop=True)
        removed = before - len(out)
        code = _code_header() + (f"df = df.dropna(subset={subset!r}).reset_index(drop=True)\n" if subset else "df = df.dropna().reset_index(drop=True)\n")
        return out, code, f"Dropped {removed:,} row(s) with missing values."
    if name == "fill_missing":
        col = op.get("column")
        strategy = op.get("strategy", "median")
        value = op.get("value")
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found.")
        out = df.copy()
        n_missing = int(out[col].isna().sum())
        code = _code_header()
        if strategy == "mean":
            v = float(out[col].mean())
            out[col] = out[col].fillna(v)
            code += f"df[{col!r}] = df[{col!r}].fillna(df[{col!r}].mean())\n"
            label = f"Filled {n_missing:,} missing value(s) in '{col}' with mean ({v:.4g})."
        elif strategy == "median":
            v = float(out[col].median()) if out[col].notna().any() else None
            out[col] = out[col].fillna(v)
            code += f"df[{col!r}] = df[{col!r}].fillna(df[{col!r}].median())\n"
            label = f"Filled {n_missing:,} missing value(s) in '{col}' with median ({v})."
        elif strategy == "mode":
            m = out[col].mode(dropna=True)
            v = m.iloc[0] if len(m) else None
            out[col] = out[col].fillna(v)
            code += f"df[{col!r}] = df[{col!r}].fillna(df[{col!r}].mode()[0])\n"
            label = f"Filled {n_missing:,} missing value(s) in '{col}' with mode ({v})."
        elif strategy == "ffill":
            out[col] = out[col].ffill()
            code += f"df[{col!r}] = df[{col!r}].ffill()\n"
            label = f"Forward-filled {n_missing:,} missing value(s) in '{col}'."
        elif strategy == "bfill":
            out[col] = out[col].bfill()
            code += f"df[{col!r}] = df[{col!r}].bfill()\n"
            label = f"Backward-filled {n_missing:,} missing value(s) in '{col}'."
        elif strategy == "constant":
            out[col] = out[col].fillna(value)
            code += f"df[{col!r}] = df[{col!r}].fillna({value!r})\n"
            label = f"Filled {n_missing:,} missing value(s) in '{col}' with {value!r}."
        elif strategy == "zero":
            out[col] = out[col].fillna(0)
            code += f"df[{col!r}] = df[{col!r}].fillna(0)\n"
            label = f"Filled {n_missing:,} missing value(s) in '{col}' with 0."
        else:
            raise ValueError(f"Unknown fill strategy '{strategy}'.")
        return out, code, label
    if name == "rename_column":
        old = op.get("old")
        new = (op.get("new") or "").strip()
        if old not in df.columns:
            raise ValueError(f"Column '{old}' not found.")
        if not new:
            raise ValueError("New column name is empty.")
        if new in df.columns:
            raise ValueError(f"Column '{new}' already exists.")
        out = df.rename(columns={old: new})
        code = _code_header() + f"df = df.rename(columns={{{old!r}: {new!r}}})\n"
        return out, code, f"Renamed '{old}' → '{new}'."
    if name == "convert_dtype":
        col = op.get("column")
        dtype = op.get("dtype")
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found.")
        out = df.copy()
        code = _code_header()
        try:
            if dtype == "numeric":
                out[col] = pd.to_numeric(out[col], errors="coerce")
                code += f"df[{col!r}] = pd.to_numeric(df[{col!r}], errors='coerce')\n"
            elif dtype == "datetime":
                out[col] = pd.to_datetime(out[col], errors="coerce")
                code += f"df[{col!r}] = pd.to_datetime(df[{col!r}], errors='coerce')\n"
            elif dtype == "string":
                out[col] = out[col].astype("string")
                code += f"df[{col!r}] = df[{col!r}].astype('string')\n"
            elif dtype == "category":
                out[col] = out[col].astype("category")
                code += f"df[{col!r}] = df[{col!r}].astype('category')\n"
            elif dtype == "int":
                out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
                code += f"df[{col!r}] = pd.to_numeric(df[{col!r}], errors='coerce').astype('Int64')\n"
            elif dtype == "float":
                out[col] = pd.to_numeric(out[col], errors="coerce").astype(float)
                code += f"df[{col!r}] = pd.to_numeric(df[{col!r}], errors='coerce').astype(float)\n"
            else:
                raise ValueError(f"Unknown dtype '{dtype}'.")
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Could not convert '{col}' to {dtype}: {e}")
        return out, code, f"Converted '{col}' to {dtype}."
    if name == "trim_whitespace":
        cols = op.get("columns") or [c for c in df.columns if df[c].dtype == object]
        if isinstance(cols, str):
            cols = [cols]
        out = df.copy()
        for c in cols:
            if c in out.columns:
                try:
                    out[c] = out[c].astype("string").str.strip()
                    # convert back if all NA-safe? keep string
                    out[c] = out[c].astype(object).where(out[c].notna(), None)
                    # restore original-ish: keep as object strings
                except Exception:
                    pass
        code = _code_header() + f"for c in {cols!r}:\n    df[c] = df[c].astype('string').str.strip()\n"
        return out, code, f"Trimmed whitespace in: {', '.join(cols)}."
    if name == "standardize_case":
        col = op.get("column")
        case = op.get("case", "lower")
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found.")
        out = df.copy()
        if case == "lower":
            out[col] = out[col].astype("string").str.strip().str.lower()
        elif case == "upper":
            out[col] = out[col].astype("string").str.strip().str.upper()
        elif case == "title":
            out[col] = out[col].astype("string").str.strip().str.title()
        else:
            raise ValueError("case must be lower|upper|title")
        code = _code_header() + f"df[{col!r}] = df[{col!r}].astype('string').str.strip().str.{case}()\n"
        return out, code, f"Standardized '{col}' to {case} case."
    if name == "cap_outliers":
        col = op.get("column")
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found.")
        out = df.copy()
        x = pd.to_numeric(out[col], errors="coerce")
        q1, q3 = x.quantile(0.25), x.quantile(0.75)
        iqr = q3 - q1
        if pd.isna(iqr) or iqr == 0:
            raise ValueError(f"'{col}' has no spread to cap (IQR = 0).")
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        out[col] = x.clip(lo, hi)
        code = _code_header() + (f"q1, q3 = df[{col!r}].quantile(0.25), df[{col!r}].quantile(0.75)\n"
                f"iqr = q3 - q1\nlo, hi = q1 - 1.5*iqr, q3 + 1.5*iqr\ndf[{col!r}] = df[{col!r}].clip(lo, hi)\n")
        return out, code, f"Capped outliers in '{col}' to [{lo:.4g}, {hi:.4g}] (1.5×IQR)."
    if name == "drop_outliers":
        col = op.get("column")
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found.")
        out = df.copy()
        x = pd.to_numeric(out[col], errors="coerce")
        q1, q3 = x.quantile(0.25), x.quantile(0.75)
        iqr = q3 - q1
        if pd.isna(iqr) or iqr == 0:
            raise ValueError(f"'{col}' has no spread (IQR = 0).")
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        before = len(out)
        out = out[(x >= lo) & (x <= hi) | (x.isna())].reset_index(drop=True)
        code = _code_header() + (f"q1, q3 = df[{col!r}].quantile(0.25), df[{col!r}].quantile(0.75)\n"
                f"iqr = q3 - q1\nlo, hi = q1 - 1.5*iqr, q3 + 1.5*iqr\ndf = df[(df[{col!r}] >= lo) & (df[{col!r}] <= hi) | (df[{col!r}].isna())].reset_index(drop=True)\n")
        return out, code, f"Removed {before - len(out):,} outlier row(s) from '{col}'."
    if name == "encode_categorical":
        col = op.get("column")
        method = op.get("method", "onehot")
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found.")
        out = df.copy()
        code = _code_header()
        if method == "onehot":
            dummies = pd.get_dummies(out[col], prefix=col, dummy_na=False)
            if dummies.shape[1] > 50:
                raise ValueError(f"'{col}' would create {dummies.shape[1]} columns — too many for one-hot encoding.")
            out = pd.concat([out.drop(columns=[col]), dummies], axis=1)
            code += f"df = pd.concat([df.drop(columns=[{col!r}]), pd.get_dummies(df[{col!r}], prefix={col!r})], axis=1)\n"
            return out, code, f"One-hot encoded '{col}' into {dummies.shape[1]} column(s)."
        elif method == "label":
            cats = sorted(out[col].dropna().astype(str).unique())
            mapping = {k: i for i, k in enumerate(cats)}
            out[col] = out[col].astype(str).map(mapping)
            code += f"cats = sorted(df[{col!r}].dropna().astype(str).unique())\nmapping = {{k: i for i, k in enumerate(cats)}}\ndf[{col!r}] = df[{col!r}].astype(str).map(mapping)\n"
            return out, code, f"Label-encoded '{col}' ({len(mapping)} categories)."
        else:
            raise ValueError("method must be onehot|label")
    if name == "scale_numeric":
        col = op.get("column")
        method = op.get("method", "standard")
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found.")
        out = df.copy()
        x = pd.to_numeric(out[col], errors="coerce")
        code = _code_header()
        if method == "standard":
            mu, sd = float(x.mean()), float(x.std())
            if not sd or pd.isna(sd):
                raise ValueError("Standard deviation is 0 — cannot standardize.")
            out[col] = (x - mu) / sd
            code += f"df[{col!r}] = (df[{col!r}] - df[{col!r}].mean()) / df[{col!r}].std()\n"
            return out, code, f"Standardized '{col}' (mean 0, std 1)."
        elif method == "minmax":
            mn, mx = float(x.min()), float(x.max())
            if mx == mn:
                raise ValueError("Min equals max — cannot min-max scale.")
            out[col] = (x - mn) / (mx - mn)
            code += f"df[{col!r}] = (df[{col!r}] - df[{col!r}].min()) / (df[{col!r}].max() - df[{col!r}].min())\n"
            return out, code, f"Min-max scaled '{col}' to [0, 1]."
        elif method == "log":
            if (x.dropna() <= 0).any():
                raise ValueError("Log transform needs positive values only.")
            out[col] = np.log1p(x)
            code += f"df[{col!r}] = np.log1p(df[{col!r}])\n"
            return out, code, f"Applied log1p transform to '{col}'."
        else:
            raise ValueError("method must be standard|minmax|log")
    raise ValueError(f"Unknown cleaning operation '{name}'.")
