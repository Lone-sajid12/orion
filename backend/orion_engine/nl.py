"""Natural-language questions → safe analytical operations (rule-based, no LLM needed).
Optional Ollama enhancement is attempted but never required."""
from __future__ import annotations
import re
import urllib.request
import json
import pandas as pd
import numpy as np
from .dtypes import classify_columns


def _find_column(question: str, df: pd.DataFrame) -> str | None:
    q = question.lower()
    # exact mention first
    for c in df.columns:
        if str(c).lower() in q:
            return c
    # token overlap
    tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", q)
    best, best_score = None, 0
    for c in df.columns:
        parts = re.findall(r"[a-zA-Z0-9]+", str(c).lower())
        score = sum(1 for p in parts if p in tokens and len(p) > 2)
        if score > best_score:
            best, best_score = c, score
    return best if best_score > 0 else None


def answer_question(df: pd.DataFrame, question: str) -> dict:
    q = (question or "").strip()
    if not q:
        raise ValueError("Please ask a question about the dataset.")
    ql = q.lower()
    roles = classify_columns(df)
    num_cols = [c for c, r in roles.items() if r == "numeric"]
    cat_cols = [c for c, r in roles.items() if r in ("categorical", "boolean")]
    dt_cols = [c for c, r in roles.items() if r == "datetime"]

    def code_wrap(code: str) -> str:
        return code

    # missing values
    if any(k in ql for k in ["missing", "null", "na ", "empty", "incomplete"]):
        miss = df.isna().sum().sort_values(ascending=False)
        miss = miss[miss > 0]
        if len(miss) == 0:
            return {"answer": "No missing values were found — every cell in the dataset is filled.",
                    "kind": "missing", "data": [], "code": code_wrap("print(df.isna().sum()[df.isna().sum() > 0])\n")}
        rows = [{"column": str(c), "missing": int(v), "pct": round(100 * v / len(df), 2)} for c, v in miss.head(20).items()]
        top = rows[0]
        return {"answer": f"{len(miss)} column(s) contain missing values. '{top['column']}' has the most: {top['missing']:,} ({top['pct']}%).",
                "kind": "missing", "data": rows, "code": code_wrap("print(df.isna().sum().sort_values(ascending=False).head(20))\n")}

    # correlations
    if "correlat" in ql:
        if len(num_cols) < 2:
            return {"answer": "Correlation needs at least 2 numeric columns, and this dataset has fewer.",
                    "kind": "correlation", "data": [], "code": ""}
        corr = df[num_cols].corr(numeric_only=True)
        pairs = []
        for i in range(len(num_cols)):
            for j in range(i + 1, len(num_cols)):
                v = corr.iloc[i, j]
                if pd.notna(v):
                    pairs.append({"x": num_cols[i], "y": num_cols[j], "r": round(float(v), 3)})
        pairs.sort(key=lambda d: abs(d["r"]), reverse=True)
        top = pairs[:5]
        if top:
            t = top[0]
            direction = "positive" if t["r"] > 0 else "negative"
            ans = (f"The strongest linear association is between '{t['x']}' and '{t['y']}' (r = {t['r']}, {direction}). "
                   f"Remember: correlation is not causation.")
        else:
            ans = "No correlations could be computed."
        return {"answer": ans, "kind": "correlation", "data": top,
                "code": code_wrap("print(df.select_dtypes(include='number').corr())\n")}

    # average / mean
    if any(k in ql for k in ["average", "mean", "median", "max", "maximum", "min", "minimum", "total", "sum"]):
        col = _find_column(q, df)
        if col is None:
            if num_cols:
                col = num_cols[0]
            else:
                return {"answer": "I couldn't find a numeric column to aggregate. Try naming a column, e.g. 'average salary'.",
                        "kind": "aggregate", "data": [], "code": ""}
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(s) == 0:
            return {"answer": f"'{col}' has no numeric values to aggregate.", "kind": "aggregate", "data": [], "code": ""}
        if "median" in ql:
            return {"answer": f"The median of '{col}' is {float(s.median()):,.4g} (n = {len(s):,}).",
                    "kind": "aggregate", "data": [{"column": col, "median": float(s.median()), "n": len(s)}],
                    "code": code_wrap(f"print(df[{col!r}].median())\n")}
        if "max" in ql:
            return {"answer": f"The maximum of '{col}' is {float(s.max()):,.4g}.",
                    "kind": "aggregate", "data": [{"column": col, "max": float(s.max())}],
                    "code": code_wrap(f"print(df[{col!r}].max())\n")}
        if "min" in ql:
            return {"answer": f"The minimum of '{col}' is {float(s.min()):,.4g}.",
                    "kind": "aggregate", "data": [{"column": col, "min": float(s.min())}],
                    "code": code_wrap(f"print(df[{col!r}].min())\n")}
        if "total" in ql or "sum" in ql:
            return {"answer": f"The total of '{col}' is {float(s.sum()):,.4g} (n = {len(s):,}).",
                    "kind": "aggregate", "data": [{"column": col, "sum": float(s.sum()), "n": len(s)}],
                    "code": code_wrap(f"print(df[{col!r}].sum())\n")}
        return {"answer": f"The average (mean) of '{col}' is {float(s.mean()):,.4g} over {len(s):,} value(s); median is {float(s.median()):,.4g}.",
                "kind": "aggregate", "data": [{"column": col, "mean": float(s.mean()), "median": float(s.median()), "n": len(s)}],
                "code": code_wrap(f"print(df[{col!r}].mean(), df[{col!r}].median())\n")}

    # highest / top category by revenue-like
    if any(k in ql for k in ["highest", "top", "largest", "best", "most"]) and ("categor" in ql or "group" in ql or "which" in ql or "by" in ql):
        if not cat_cols or not num_cols:
            pass
        else:
            # pick numeric: mentioned or first; categorical: mentioned or first
            ncol = None
            for c in num_cols:
                if str(c).lower() in ql:
                    ncol = c
                    break
            ncol = ncol or num_cols[0]
            ccol = None
            for c in cat_cols:
                if str(c).lower() in ql:
                    ccol = c
                    break
            ccol = ccol or cat_cols[0]
            g = df.groupby(df[ccol].astype(str))[ncol].mean(numeric_only=True).sort_values(ascending=False)
            if len(g):
                return {"answer": f"By average '{ncol}', the top '{ccol}' is '{g.index[0]}' ({float(g.iloc[0]):,.4g}).",
                        "kind": "groupby", "data": [{"group": str(i)[:60], "mean": float(v)} for i, v in g.head(10).items()],
                        "code": code_wrap(f"print(df.groupby({ccol!r})[{ncol!r}].mean().sort_values(ascending=False).head(10))\n")}

    # trend
    if "trend" in ql or "over time" in ql or "monthly" in ql or "yearly" in ql or "daily" in ql:
        if not dt_cols or not num_cols:
            return {"answer": "A trend needs a datetime column and a numeric column. This dataset doesn't have both.",
                    "kind": "trend", "data": [], "code": ""}
        dc = dt_cols[0]
        ncol = num_cols[0]
        for c in num_cols:
            if str(c).lower() in ql:
                ncol = c
                break
        t = pd.to_datetime(df[dc], errors="coerce")
        tmp = pd.DataFrame({"t": t, "y": pd.to_numeric(df[ncol], errors="coerce")}).dropna().sort_values("t")
        if len(tmp) < 6:
            return {"answer": "Not enough dated observations to describe a trend.", "kind": "trend", "data": [], "code": ""}
        k = max(1, len(tmp) // 3)
        first, last = float(tmp.iloc[:k]["y"].mean()), float(tmp.iloc[-k:]["y"].mean())
        direction = "up" if last > first else ("down" if last < first else "flat")
        pct = (100 * (last - first) / abs(first)) if first != 0 else 0
        return {"answer": f"'{ncol}' trends {direction} over '{dc}': early average {first:,.4g} → recent average {last:,.4g} ({pct:+.1f}%). Open Visualize for the full time-series chart.",
                "kind": "trend", "data": [{"early_mean": first, "recent_mean": last, "pct_change": round(pct, 2)}],
                "code": code_wrap(f"df.set_index(pd.to_datetime(df[{dc!r}])).sort_index()[{ncol!r}].plot()\n")}

    # unusual / outliers
    if any(k in ql for k in ["unusual", "outlier", "anomal", "weird", "strange"]):
        if not num_cols:
            return {"answer": "Outlier detection needs a numeric column.", "kind": "outliers", "data": [], "code": ""}
        col = _find_column(q, df)
        if col not in num_cols:
            col = num_cols[0]
        s = pd.to_numeric(df[col], errors="coerce")
        x = s.dropna()
        q1, q3 = x.quantile(0.25), x.quantile(0.75)
        iqr = q3 - q1
        if pd.isna(iqr) or iqr == 0:
            return {"answer": f"'{col}' has no spread (IQR = 0), so outlier detection isn't meaningful.", "kind": "outliers", "data": [], "code": ""}
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        idx = s[(s < lo) | (s > hi)].dropna()
        return {"answer": f"Found {len(idx)} potential outlier(s) in '{col}' outside [{lo:.4g}, {hi:.4g}] (1.5×IQR rule).",
                "kind": "outliers", "data": [{"index": int(i), "value": float(v)} for i, v in idx.head(20).items()],
                "code": code_wrap(f"q1, q3 = df[{col!r}].quantile([0.25, 0.75])\niqr = q3-q1\nprint(df[(df[{col!r}] < q1-1.5*iqr) | (df[{col!r}] > q3+1.5*iqr)])\n")}

    # shape / overview
    if any(k in ql for k in ["how many", "shape", "size", "rows", "columns", "overview", "describe", "summary"]):
        return {"answer": f"The dataset has {df.shape[0]:,} rows and {df.shape[1]} columns: {len(num_cols)} numeric, {len(cat_cols)} categorical, {len(dt_cols)} datetime. {int(df.isna().sum().sum()):,} cells are missing.",
                "kind": "overview", "data": [{"rows": df.shape[0], "columns": df.shape[1]}],
                "code": code_wrap("print(df.shape)\nprint(df.dtypes)\nprint(df.isna().sum())\n")}

    # distribution of a column
    col = _find_column(q, df)
    if col is not None:
        role = roles.get(col)
        if role == "numeric":
            s = pd.to_numeric(df[col], errors="coerce").dropna()
            return {"answer": f"'{col}': mean {float(s.mean()):,.4g}, median {float(s.median()):,.4g}, std {float(s.std()):,.4g}, range [{float(s.min()):,.4g}, {float(s.max()):,.4g}] (n={len(s):,}).",
                    "kind": "describe", "data": [{"column": col}], "code": code_wrap(f"print(df[{col!r}].describe())\n")}
        else:
            vc = df[col].value_counts(dropna=True).head(5)
            tops = ", ".join(f"'{i}' ({c:,})" for i, c in vc.items())
            return {"answer": f"'{col}' has {int(df[col].nunique(dropna=True)):,} distinct values. Most common: {tops}.",
                    "kind": "describe", "data": [{"value": str(i), "count": int(c)} for i, c in vc.items()],
                    "code": code_wrap(f"print(df[{col!r}].value_counts().head())\n")}

    # fallback: guided help (honest, not fake AI)
    return {"answer": ("I can answer concrete questions from your data, for example: 'What is the average of {col}?', "
                       "'Which columns have missing values?', 'What are the strongest correlations?', "
                       "'Show monthly trend', 'Find unusual records'. Try naming one of your columns: "
                       + ", ".join(list(df.columns)[:6]) + "."),
            "kind": "help", "data": [], "code": ""}


def ollama_status() -> dict:
    """Probe local Ollama (optional). Never required."""
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as r:
            data = json.loads(r.read().decode("utf-8", errors="ignore"))
            models = [m.get("name", "") for m in data.get("models", [])]
            return {"available": True, "models": models}
    except Exception:
        return {"available": False, "models": []}


def ollama_explain(prompt: str, model: str = "") -> dict:
    """Optional: ask local Ollama for an explanation. Fails gracefully."""
    try:
        # pick model
        status = ollama_status()
        if not status["available"]:
            raise RuntimeError("Ollama is not running on localhost:11434.")
        use_model = model or (status["models"][0] if status["models"] else "")
        if not use_model:
            raise RuntimeError("No local models found in Ollama. Run `ollama pull llama3.1` first.")
        body = json.dumps({"model": use_model, "prompt": prompt, "stream": False}).encode()
        req = urllib.request.Request("http://localhost:11434/api/generate", data=body,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8", errors="ignore"))
            return {"ok": True, "model": use_model, "response": data.get("response", "")}
    except Exception as e:
        return {"ok": False, "error": str(e)}
