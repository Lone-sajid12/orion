"""Rule-based automatic insights from real data. No invented claims."""
from __future__ import annotations
import pandas as pd
import numpy as np
from .dtypes import classify_columns


def generate_insights(df: pd.DataFrame, max_insights: int = 12) -> dict:
    roles = classify_columns(df)
    n = len(df)
    insights: list[dict] = []

    def add(kind: str, title: str, detail: str, columns: list[str], severity: str = "info", metric: dict | None = None):
        insights.append({"kind": kind, "title": title, "detail": detail, "columns": columns,
                         "severity": severity, "metric": metric or {}})

    # 1. strongest correlations
    try:
        num = df.select_dtypes(include=[np.number])
        if num.shape[1] >= 2:
            corr = num.corr(numeric_only=True)
            pairs = []
            cols = corr.columns.tolist()
            for i in range(len(cols)):
                for j in range(i + 1, len(cols)):
                    v = corr.iloc[i, j]
                    if pd.notna(v):
                        pairs.append((cols[i], cols[j], float(v)))
            pairs.sort(key=lambda t: abs(t[2]), reverse=True)
            for a, b, r in pairs[:3]:
                if abs(r) >= 0.5:
                    direction = "positive" if r > 0 else "negative"
                    strength = "very strong" if abs(r) >= 0.85 else ("strong" if abs(r) >= 0.7 else "moderate-to-strong")
                    add("correlation", f"{a} and {b} show a {strength} {direction} correlation (r = {r:.2f})",
                        f"The Pearson correlation between '{a}' and '{b}' is {r:.3f}. This is an association in the observed data — it does not establish that one causes the other.",
                        [a, b], "info", {"r": round(r, 4)})
                else:
                    break
            if pairs and abs(pairs[0][2]) < 0.3:
                a, b, r = pairs[0]
                add("correlation", f"No strong linear correlations found (strongest: r = {r:.2f})",
                    f"The strongest linear association among numeric columns is '{a}' ↔ '{b}' at r = {r:.3f}. Relationships may still exist that are non-linear or involve categories.",
                    [a, b], "info", {"r": round(r, 4)})
    except Exception:
        pass

    # 2. missing data
    miss = df.isna().sum().sort_values(ascending=False)
    for col, k in miss.head(3).items():
        if k > 0:
            pct = 100 * k / n if n else 0
            sev = "warning" if pct >= 5 else "info"
            add("missing", f"'{col}' is missing {pct:.1f}% of values",
                f"'{col}' has {int(k):,} missing value(s) out of {n:,} rows. Check whether missingness is random or systematic before imputing.",
                [col], sev, {"missing": int(k), "pct": round(pct, 2)})

    # 3. dominant categories
    for col, role in roles.items():
        if role in ("categorical", "boolean"):
            try:
                vc = df[col].value_counts(dropna=True, normalize=True)
                if len(vc) and vc.iloc[0] >= 0.6:
                    add("dominance", f"'{vc.index[0]}' dominates '{col}' ({vc.iloc[0]*100:.1f}%)",
                        f"One category accounts for {vc.iloc[0]*100:.1f}% of '{col}'. Imbalanced categories can skew models and deserve stratified evaluation.",
                        [col], "info", {"top": str(vc.index[0]), "pct": round(float(vc.iloc[0]) * 100, 1)})
            except Exception:
                pass

    # 4. skew / unusual distributions
    for col, role in roles.items():
        if role == "numeric":
            try:
                s = pd.to_numeric(df[col], errors="coerce").dropna()
                if len(s) > 10:
                    sk = float(s.skew())
                    if abs(sk) >= 1.0:
                        direction = "right-skewed (long tail of large values)" if sk > 0 else "left-skewed (long tail of small values)"
                        add("distribution", f"'{col}' is strongly {direction} (skew = {sk:.2f})",
                            f"'{col}' has skew {sk:.2f}. The median may describe the typical value better than the mean; consider a log transform before modelling.",
                            [col], "info", {"skew": round(sk, 3)})
            except Exception:
                pass

    # 5. group differences (numeric vs top categorical)
    try:
        num_cols = [c for c, r in roles.items() if r == "numeric"][:6]
        cat_cols = [c for c, r in roles.items() if r in ("categorical", "boolean")][:4]
        for nc in num_cols[:3]:
            s = pd.to_numeric(df[nc], errors="coerce")
            if s.notna().sum() < 10:
                continue
            overall = float(s.mean())
            sd = float(s.std()) or 1.0
            for cc in cat_cols[:2]:
                try:
                    g = df.groupby(df[cc].astype(str))[nc].mean(numeric_only=True).dropna()
                    if len(g) >= 2:
                        top_g = g.idxmax(); bot_g = g.idxmin()
                        diff_sd = abs(float(g.max() - g.min())) / sd
                        if diff_sd >= 1.0:
                            add("group_difference",
                                f"Average '{nc}' differs notably across '{cc}' ({float(g.max()):.3g} vs {float(g.min()):.3g})",
                                f"Mean '{nc}' is highest for '{top_g}' ({float(g.max()):.4g}) and lowest for '{bot_g}' ({float(g.min()):.4g}) — a gap of {diff_sd:.1f} standard deviations. Use a t-test/ANOVA in Statistics Lab before concluding the difference is significant.",
                                [nc, cc], "info", {"gap_sd": round(diff_sd, 2)})
                            break
                except Exception:
                    continue
    except Exception:
        pass

    # 6. trends over time
    try:
        dt_cols = [c for c, r in roles.items() if r == "datetime"]
        num_cols = [c for c, r in roles.items() if r == "numeric"]
        if dt_cols and num_cols:
            dc = dt_cols[0]
            t = pd.to_datetime(df[dc], errors="coerce")
            for nc in num_cols[:3]:
                try:
                    tmp = pd.DataFrame({"t": t, "y": pd.to_numeric(df[nc], errors="coerce")}).dropna()
                    if len(tmp) < 12:
                        continue
                    tmp = tmp.sort_values("t")
                    # compare first vs last third
                    k = len(tmp) // 3
                    first = tmp.iloc[:k]["y"].mean()
                    last = tmp.iloc[-k:]["y"].mean()
                    if pd.notna(first) and pd.notna(last) and first != 0:
                        pct = 100 * (last - first) / abs(first)
                        if abs(pct) >= 20:
                            direction = "increased" if pct > 0 else "decreased"
                            add("trend", f"'{nc}' has {direction} {abs(pct):.0f}% from the earliest to the latest period",
                                f"Comparing the earliest third to the latest third by '{dc}', mean '{nc}' moved from {first:.4g} to {last:.4g}. Inspect the time-series chart to confirm the pattern is sustained rather than a spike.",
                                [dc, nc], "info", {"pct_change": round(pct, 1)})
                            break
                except Exception:
                    continue
    except Exception:
        pass

    # 7. outliers summary
    try:
        for col, role in roles.items():
            if role == "numeric":
                s = pd.to_numeric(df[col], errors="coerce").dropna()
                if len(s) >= 20:
                    q1, q3 = s.quantile(0.25), s.quantile(0.75)
                    iqr = q3 - q1
                    if iqr and not pd.isna(iqr):
                        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                        k = int(((s < lo) | (s > hi)).sum())
                        if k >= max(5, 0.02 * len(s)):
                            add("outliers", f"'{col}' has {k} potential outlier(s)",
                                f"{k} value(s) in '{col}' fall outside 1.5×IQR [{lo:.4g}, {hi:.4g}]. Review these records — they may be data errors or important edge cases.",
                                [col], "warning", {"count": k})
                            break
    except Exception:
        pass

    # 8. duplicates
    try:
        d = int(df.duplicated().sum())
        if d > 0:
            add("duplicates", f"{d:,} duplicate row(s) found ({100*d/n:.1f}% of data)" if n else f"{d} duplicates",
                "Exact duplicate rows inflate sample size and can leak across train/test splits. Consider removing them in Data Quality.",
                [], "warning" if d / max(n, 1) >= 0.01 else "info", {"count": d})
    except Exception:
        pass

    # 9. cardinality / identifiers
    for col, role in roles.items():
        if role in ("categorical", "text") and n > 0:
            try:
                u = int(df[col].nunique(dropna=True))
                if u == n and n > 5:
                    add("identifier", f"'{col}' looks like a unique identifier",
                        f"'{col}' has {u:,} distinct values for {n:,} rows — likely an ID. IDs rarely help models and are usually excluded from features.",
                        [col], "info", {"unique": u})
                    break
            except Exception:
                pass

    # cap + order: warnings first
    insights.sort(key=lambda d: (0 if d["severity"] == "warning" else 1, d["kind"]))
    return {"count": len(insights), "insights": insights[:max_insights],
            "note": "Insights are heuristic observations from your data, not conclusions. Verify important findings with charts and tests."}
