"""EDA + visualization data builders. Returns JSON-serializable plot specs."""
from __future__ import annotations
import math
import pandas as pd
import numpy as np
from .dtypes import classify_columns

MAX_POINTS = 5000


def _downsample(x: list, y: list | None = None, n: int = MAX_POINTS, seed: int = 7):
    if len(x) <= n:
        return (x, y) if y is not None else x
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(x), size=n, replace=False)
    idx.sort()
    xs = [x[i] for i in idx]
    if y is None:
        return xs
    ys = [y[i] for i in idx]
    return xs, ys


def _clean_num(s: pd.Series) -> list[float]:
    x = pd.to_numeric(s, errors="coerce").dropna().tolist()
    return [float(v) for v in x if v is not None and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))]


def univariate(df: pd.DataFrame, col: str) -> dict:
    if col not in df.columns:
        raise ValueError(f"Column '{col}' not found")
    roles = classify_columns(df)
    role = roles.get(col, "text")
    s = df[col]
    if role == "numeric":
        vals = _clean_num(s)
        if not vals:
            raise ValueError(f"'{col}' has no valid numeric values.")
        arr = np.array(vals, dtype=float)
        q = np.quantile(arr, [0, 0.25, 0.5, 0.75, 1.0])
        stats = {
            "count": len(arr), "mean": float(arr.mean()), "median": float(np.median(arr)),
            "std": float(arr.std(ddof=1)) if len(arr) > 1 else 0.0,
            "min": float(q[0]), "q1": float(q[1]), "q3": float(q[3]), "max": float(q[4]),
            "range": float(q[4] - q[0]), "iqr": float(q[3] - q[1]),
        }
        try:
            from scipy import stats as sc
            stats["skew"] = float(sc.skew(arr)) if len(arr) > 2 else 0.0
            stats["kurtosis"] = float(sc.kurtosis(arr)) if len(arr) > 3 else 0.0
        except Exception:
            stats["skew"] = 0.0
            stats["kurtosis"] = 0.0
        # histogram bins
        hist_vals = vals if len(vals) <= 20000 else _downsample(vals, n=20000)
        counts, edges = np.histogram(hist_vals, bins=min(40, max(10, int(len(hist_vals) ** 0.5 // 2))))
        plot_vals = _downsample(vals, n=MAX_POINTS)
        return {
            "column": col, "role": role, "stats": stats,
            "plots": {
                "histogram": {"counts": counts.tolist(), "edges": edges.tolist()},
                "box": {"values": plot_vals},
            },
            "code": f"import pandas as pd\ns = df[{col!r}]\nprint(s.describe())\nprint('skew:', s.skew())\n",
        }
    else:
        vc = s.astype("string").value_counts(dropna=True)
        total = int(s.notna().sum())
        top = vc.head(20)
        data = [{"value": str(i)[:80], "count": int(c), "pct": round(100 * c / total, 2) if total else 0} for i, c in top.items()]
        return {
            "column": col, "role": role,
            "stats": {"count": total, "unique": int(s.nunique(dropna=True)),
                      "mode": str(vc.index[0]) if len(vc) else None,
                      "mode_count": int(vc.iloc[0]) if len(vc) else 0,
                      "missing": int(s.isna().sum())},
            "plots": {"bars": data, "other_count": int(vc[20:].sum()) if len(vc) > 20 else 0},
            "code": f"import pandas as pd\nprint(df[{col!r}].value_counts(dropna=False).head(20))\nprint(df[{col!r}].nunique(), 'distinct values')\n",
        }


def correlation_matrix(df: pd.DataFrame, method: str = "pearson", max_cols: int = 25) -> dict:
    num = df.select_dtypes(include=[np.number])
    if num.shape[1] < 2:
        raise ValueError("Need at least 2 numeric columns for a correlation matrix.")
    if num.shape[1] > max_cols:
        # keep highest-variance cols
        var = num.var(numeric_only=True).sort_values(ascending=False)
        num = num[var.head(max_cols).index.tolist()]
    if method not in ("pearson", "spearman", "kendall"):
        method = "pearson"
    corr = num.corr(method=method, numeric_only=True)
    cols = corr.columns.tolist()
    mat = [[(None if pd.isna(v) else round(float(v), 4)) for v in row] for row in corr.values.tolist()]
    # strongest pairs
    pairs = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            v = corr.iloc[i, j]
            if pd.isna(v):
                continue
            pairs.append({"x": cols[i], "y": cols[j], "r": round(float(v), 4), "abs": abs(float(v))})
    pairs.sort(key=lambda d: d["abs"], reverse=True)
    code = ("import pandas as pd\nnum = df.select_dtypes(include='number')\n"
            f"corr = num.corr(method={method!r})\nprint(corr)\n")
    return {"method": method, "columns": cols, "matrix": mat, "pairs": pairs[:15], "code": code}


def build_chart(df: pd.DataFrame, spec: dict) -> dict:
    """spec: {type, x, y, group, agg, bins, top_n, sort}"""
    ctype = (spec.get("type") or "bar").lower()
    xcol = spec.get("x")
    ycol = spec.get("y")
    group = spec.get("group")
    agg = (spec.get("agg") or "mean").lower()
    bins = int(spec.get("bins") or 30)
    top_n = int(spec.get("top_n") or 15)

    def aggfunc(s: pd.Series):
        if agg == "sum":
            return s.sum()
        if agg == "median":
            return s.median()
        if agg == "min":
            return s.min()
        if agg == "max":
            return s.max()
        if agg == "count":
            return s.count()
        return s.mean()

    if ctype == "histogram":
        col = xcol or ycol
        if not col or col not in df.columns:
            raise ValueError("Choose a column for the histogram.")
        vals = _clean_num(df[col])
        if not vals:
            raise ValueError(f"'{col}' has no numeric values to plot.")
        bins = min(60, max(5, bins))
        counts, edges = np.histogram(vals, bins=bins)
        return {"type": "histogram", "x": col, "counts": counts.tolist(), "edges": edges.tolist(),
                "code": f"import matplotlib.pyplot as plt\ndf[{col!r}].hist(bins={bins})\nplt.xlabel({col!r})\nplt.show()\n"}
    if ctype == "box":
        if not ycol or ycol not in df.columns:
            raise ValueError("Choose a numeric Y column for the box plot.")
        yv = pd.to_numeric(df[ycol], errors="coerce")
        if group and group in df.columns:
            cats = df[group].astype(str).fillna("(missing)")
            top = cats.value_counts().head(12).index.tolist()
            series = []
            for c in top:
                vals = _clean_num(yv[cats == c])
                if vals:
                    series.append({"name": str(c)[:40], "values": _downsample(vals, n=2000)})
            return {"type": "box", "y": ycol, "group": group, "series": series,
                    "code": f"import seaborn as sns\nsns.boxplot(data=df, x={group!r}, y={ycol!r})\n"}
        vals = _clean_num(yv)
        return {"type": "box", "y": ycol, "series": [{"name": ycol, "values": _downsample(vals, n=5000)}],
                "code": f"df.boxplot(column={ycol!r})\n"}
    if ctype == "scatter":
        if not xcol or not ycol or xcol not in df.columns or ycol not in df.columns:
            raise ValueError("Choose numeric X and Y columns for a scatter plot.")
        a = pd.to_numeric(df[xcol], errors="coerce")
        b = pd.to_numeric(df[ycol], errors="coerce")
        m = a.notna() & b.notna()
        xs = a[m].astype(float).tolist()
        ys = b[m].astype(float).tolist()
        xs, ys = _downsample(xs, ys, n=MAX_POINTS)
        trace = {"x": xs, "y": ys}
        if group and group in df.columns:
            cats = df.loc[m, group].astype(str).tolist()
            # downsample consistently
            if len(xs) == MAX_POINTS or len(cats) > MAX_POINTS:
                rng = np.random.default_rng(7)
                idx = sorted(rng.choice(len(df.loc[m]), size=min(MAX_POINTS, int(m.sum())), replace=False).tolist())
                full_x = a[m].astype(float).tolist()
                full_y = b[m].astype(float).tolist()
                full_c = df.loc[m, group].astype(str).tolist()
                xs = [full_x[i] for i in idx]; ys = [full_y[i] for i in idx]
                trace["color"] = [full_c[i][:40] for i in idx]
            else:
                trace["color"] = [c[:40] for c in cats[:len(xs)]]
            trace["color_label"] = group
        code = f"import matplotlib.pyplot as plt\nplt.scatter(df[{xcol!r}], df[{ycol!r}], alpha=0.5)\nplt.xlabel({xcol!r}); plt.ylabel({ycol!r})\nplt.show()\n"
        return {"type": "scatter", "x": xcol, "y": ycol, **trace, "code": code}
    if ctype in ("bar", "line", "area"):
        if not xcol or xcol not in df.columns:
            raise ValueError("Choose an X column.")
        roles = classify_columns(df)
        # numeric aggregation vs category
        if ycol and ycol in df.columns and pd.api.types.is_numeric_dtype(df[ycol]):
            if group and group in df.columns:
                g = df.groupby([df[xcol].astype(str), df[group].astype(str)], dropna=False)[ycol].apply(aggfunc).reset_index()
                g.columns = ["x", "g", "y"]
                # limit categories
                top_g = df[group].astype(str).value_counts().head(6).index.tolist()
                g = g[g["g"].isin(top_g)]
                # limit x
                top_x = df[xcol].astype(str).value_counts().head(30).index.tolist()
                g = g[g["x"].isin(top_x)]
                series = []
                for gv in top_g:
                    sub = g[g["g"] == gv].sort_values("x")
                    series.append({"name": str(gv)[:40], "x": sub["x"].astype(str).tolist(), "y": [float(v) if pd.notna(v) else None for v in sub["y"].tolist()]})
                # union x order
                xs = sorted(set(sum([s["x"] for s in series], [])), key=lambda v: top_x.index(v) if v in top_x else 999)
                # realign
                for s in series:
                    m = dict(zip(s["x"], s["y"]))
                    s["x"] = xs
                    s["y"] = [m.get(v) for v in xs]
                code = f"df.groupby([{xcol!r}, {group!r}])[{ycol!r}].{agg}().unstack().plot(kind={'bar' if ctype=='bar' else 'line'})\n"
                return {"type": ctype, "x": xs, "series": series, "ylabel": f"{agg}({ycol})", "code": code}
            else:
                # x categorical or binned numeric or datetime
                if roles.get(xcol) == "datetime":
                    t = pd.to_datetime(df[xcol], errors="coerce")
                    tmp = pd.DataFrame({"t": t, "y": pd.to_numeric(df[ycol], errors="coerce")}).dropna(subset=["t"])
                    if len(tmp) == 0:
                        raise ValueError("No valid dates to plot.")
                    tmp = tmp.set_index("t").sort_index()
                    rule = "ME" if (tmp.index.max() - tmp.index.min()).days > 120 else ("W" if (tmp.index.max() - tmp.index.min()).days > 21 else "D")
                    res = tmp["y"].resample(rule).apply(aggfunc if agg != "count" else "count")
                    xs = [d.isoformat() for d in res.index.tolist()]
                    ys = [float(v) if pd.notna(v) else None for v in res.values.tolist()]
                    code = f"df.set_index(pd.to_datetime(df[{xcol!r}])).resample('{rule}')[{ycol!r}].{agg}().plot()\n"
                    return {"type": ctype, "x": xs, "series": [{"name": f"{agg}({ycol})", "x": xs, "y": ys}], "ylabel": f"{agg}({ycol})", "code": code}
                g = df.groupby(df[xcol].astype(str), dropna=False)[ycol].apply(aggfunc).reset_index()
                g.columns = ["x", "y"]
                # order: by y desc for bar, keep top_n
                g = g.sort_values("y", ascending=False).head(top_n)
                if ctype != "bar":
                    # try natural sort
                    try:
                        g = g.sort_values("x")
                    except Exception:
                        pass
                xs = g["x"].astype(str).str.slice(0, 40).tolist()
                ys = [float(v) if pd.notna(v) else None for v in g["y"].tolist()]
                code = f"df.groupby({xcol!r})[{ycol!r}].{agg}().sort_values(ascending=False).head({top_n}).plot(kind={'bar' if ctype=='bar' else 'line'})\n"
                return {"type": ctype, "x": xs, "series": [{"name": f"{agg}({ycol})", "x": xs, "y": ys}], "ylabel": f"{agg}({ycol})", "code": code}
        else:
            # frequency of x
            vc = df[xcol].astype(str).value_counts(dropna=False).head(top_n)
            xs = [str(i)[:40] for i in vc.index.tolist()]
            ys = [int(v) for v in vc.values.tolist()]
            code = f"df[{xcol!r}].value_counts().head({top_n}).plot(kind='bar')\n"
            return {"type": "bar", "x": xs, "series": [{"name": "count", "x": xs, "y": ys}], "ylabel": "count", "code": code}
    if ctype in ("pie", "donut"):
        col = xcol or group
        if not col or col not in df.columns:
            raise ValueError("Choose a categorical column for pie/donut.")
        vc = df[col].astype(str).value_counts(dropna=True)
        if len(vc) > 12:
            raise ValueError(f"'{col}' has {len(vc)} categories — a pie chart would be unreadable. Use a bar chart instead.")
        labels = [str(i)[:40] for i in vc.index.tolist()]
        values = [int(v) for v in vc.values.tolist()]
        return {"type": ctype, "labels": labels, "values": values,
                "code": f"df[{col!r}].value_counts().plot(kind='pie', autopct='%1.1f%%')\n"}
    if ctype == "heatmap":
        res = correlation_matrix(df, method="pearson" if (spec.get("method") in (None, "")) else spec.get("method", "pearson"))
        res["type"] = "heatmap"
        return res
    raise ValueError(f"Unknown chart type '{ctype}'.")


def bivariate(df: pd.DataFrame, x: str, y: str) -> dict:
    if x not in df.columns or y not in df.columns:
        raise ValueError("Choose two valid columns.")
    roles = classify_columns(df)
    rx, ry = roles.get(x), roles.get(y)
    # recommend chart
    if rx == "numeric" and ry == "numeric":
        chart = build_chart(df, {"type": "scatter", "x": x, "y": y})
        try:
            r = float(pd.to_numeric(df[x], errors="coerce").corr(pd.to_numeric(df[y], errors="coerce")))
        except Exception:
            r = None
        return {"x": x, "y": y, "recommendation": "scatter", "correlation": r, "chart": chart}
    if rx == "datetime" and ry == "numeric":
        chart = build_chart(df, {"type": "line", "x": x, "y": y})
        return {"x": x, "y": y, "recommendation": "line", "chart": chart}
    if ry == "datetime" and rx == "numeric":
        chart = build_chart(df, {"type": "line", "x": y, "y": x})
        return {"x": x, "y": y, "recommendation": "line", "chart": chart}
    if rx == "numeric" and ry in ("categorical", "boolean"):
        chart = build_chart(df, {"type": "box", "y": x, "group": y})
        # group means
        g = df.groupby(df[y].astype(str))[x].mean(numeric_only=True).sort_values(ascending=False).head(10)
        return {"x": x, "y": y, "recommendation": "box", "chart": chart,
                "group_means": [{"group": str(i)[:40], "mean": float(v)} for i, v in g.items() if pd.notna(v)]}
    if ry == "numeric" and rx in ("categorical", "boolean"):
        chart = build_chart(df, {"type": "box", "y": y, "group": x})
        g = df.groupby(df[x].astype(str))[y].mean(numeric_only=True).sort_values(ascending=False).head(10)
        return {"x": x, "y": y, "recommendation": "box", "chart": chart,
                "group_means": [{"group": str(i)[:40], "mean": float(v)} for i, v in g.items() if pd.notna(v)]}
    # categorical x categorical -> crosstab heatmap-ish stacked bars
    ct = pd.crosstab(df[x].astype(str), df[y].astype(str))
    if ct.shape[0] > 20 or ct.shape[1] > 12:
        # trim
        topx = df[x].astype(str).value_counts().head(15).index
        topy = df[y].astype(str).value_counts().head(8).index
        ct = pd.crosstab(df[x].astype(str), df[y].astype(str)).loc[[i for i in topx if i in ct.index], [j for j in topy if j in ct.columns]]
    return {"x": x, "y": y, "recommendation": "crosstab",
            "crosstab": {"rows": [str(i)[:40] for i in ct.index.tolist()],
                         "cols": [str(j)[:40] for j in ct.columns.tolist()],
                         "values": ct.values.tolist()},
            "code": f"import pandas as pd\nprint(pd.crosstab(df[{x!r}], df[{y!r}]))\n"}
