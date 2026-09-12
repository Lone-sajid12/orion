"""Descriptive stats, correlations, hypothesis tests with plain-language explanations."""
from __future__ import annotations
import math
import pandas as pd
import numpy as np


def _f(v):
    if v is None:
        return None
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except Exception:
        return None


def _explain_p(p: float | None, alpha: float = 0.05) -> str:
    if p is None:
        return "The p-value could not be computed for this test."
    if p < 0.001:
        sig = "highly statistically significant"
    elif p < alpha:
        sig = "statistically significant"
    else:
        sig = "not statistically significant"
    verdict = "Reject the null hypothesis." if (p < alpha) else "Fail to reject the null hypothesis."
    return (f"p = {p:.4g}. At the {alpha:.0%} significance level this result is {sig}. {verdict} "
            f"This describes association in the observed data — it does not prove causation.")


def descriptive(df: pd.DataFrame, columns: list[str] | None = None) -> dict:
    num = df.select_dtypes(include=[np.number])
    if columns:
        cols = [c for c in columns if c in num.columns]
        if not cols:
            raise ValueError("No valid numeric columns selected.")
        num = num[cols]
    if num.shape[1] == 0:
        raise ValueError("No numeric columns available for descriptive statistics.")
    desc = num.describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).T
    rows = []
    for c in desc.index:
        s = num[c]
        rows.append({
            "column": c, "count": int(s.count()),
            "mean": _f(desc.loc[c, "mean"]), "std": _f(desc.loc[c, "std"]),
            "min": _f(desc.loc[c, "min"]), "p5": _f(desc.loc[c, "5%"]),
            "q1": _f(desc.loc[c, "25%"]), "median": _f(desc.loc[c, "50%"]),
            "q3": _f(desc.loc[c, "75%"]), "p95": _f(desc.loc[c, "95%"]),
            "max": _f(desc.loc[c, "max"]),
            "skew": _f(s.skew()), "kurtosis": _f(s.kurt()),
            "missing": int(s.isna().sum()),
        })
    code = "desc = df.describe(percentiles=[.05,.25,.5,.75,.95]).T\nprint(desc)\n"
    return {"rows": rows, "code": code}


def correlation(df: pd.DataFrame, x: str, y: str, method: str = "pearson") -> dict:
    if x not in df.columns or y not in df.columns:
        raise ValueError("Choose two valid columns.")
    a = pd.to_numeric(df[x], errors="coerce")
    b = pd.to_numeric(df[y], errors="coerce")
    m = a.notna() & b.notna()
    if m.sum() < 3:
        raise ValueError("Not enough paired numeric observations (need ≥ 3).")
    if method not in ("pearson", "spearman", "kendall"):
        method = "pearson"
    r = float(a[m].corr(b[m], method=method))
    # p-value via scipy
    p = None
    try:
        from scipy import stats as sc
        if method == "pearson":
            _, p = sc.pearsonr(a[m], b[m])
        elif method == "spearman":
            _, p = sc.spearmanr(a[m], b[m])
        else:
            _, p = sc.kendalltau(a[m], b[m])
        p = float(p)
    except Exception:
        p = None
    strength = "negligible" if abs(r) < 0.1 else ("weak" if abs(r) < 0.3 else ("moderate" if abs(r) < 0.6 else ("strong" if abs(r) < 0.85 else "very strong")))
    direction = "positive" if r > 0 else ("negative" if r < 0 else "no")
    explanation = (f"{x} and {y} show a {strength} {direction} {method} correlation (r = {r:.3f}, n = {int(m.sum())}). "
                   + _explain_p(p) + " Correlation measures linear association only (for Pearson).")
    code = (f"from scipy import stats\nr, p = stats.{'pearsonr' if method=='pearson' else ('spearmanr' if method=='spearman' else 'kendalltau')}"
            f"(df[{x!r}].dropna(), df[{y!r}].dropna())\nprint(r, p)\n")
    return {"x": x, "y": y, "method": method, "r": _f(r), "p_value": _f(p), "n": int(m.sum()),
            "strength": strength, "direction": direction, "explanation": explanation, "code": code}


def confidence_interval(df: pd.DataFrame, column: str, level: float = 0.95) -> dict:
    if column not in df.columns:
        raise ValueError("Choose a valid column.")
    x = pd.to_numeric(df[column], errors="coerce").dropna()
    if len(x) < 2:
        raise ValueError("Need at least 2 observations.")
    if not 0.5 < level < 0.999:
        raise ValueError("Confidence level must be between 0.5 and 0.999.")
    try:
        from scipy import stats as sc
        res = sc.t.interval(level, len(x) - 1, loc=float(x.mean()), scale=float(sc.sem(x)))
        lo, hi = float(res[0]), float(res[1])
    except Exception as e:
        raise ValueError(f"Could not compute confidence interval: {e}")
    explanation = (f"We are {level:.0%} confident the true population mean of '{column}' lies between {lo:.4g} and {hi:.4g} "
                   f"(sample mean {float(x.mean()):.4g}, n = {len(x)}), assuming roughly independent observations.")
    code = (f"from scipy import stats\nstats.t.interval({level}, len(df)-1, loc=df[{column!r}].mean(), scale=stats.sem(df[{column!r}].dropna()))\n")
    return {"column": column, "level": level, "mean": _f(float(x.mean())), "n": len(x),
            "ci_low": _f(lo), "ci_high": _f(hi), "explanation": explanation, "code": code}


def ttest(df: pd.DataFrame, numeric_col: str, group_col: str, group_a: str | None = None, group_b: str | None = None) -> dict:
    from scipy import stats as sc
    if numeric_col not in df.columns or group_col not in df.columns:
        raise ValueError("Choose a numeric column and a grouping column.")
    x = pd.to_numeric(df[numeric_col], errors="coerce")
    g = df[group_col].astype(str)
    cats = g[x.notna()].value_counts()
    if len(cats) < 2:
        raise ValueError("Grouping column needs at least 2 groups.")
    a = group_a or str(cats.index[0])
    b = group_b or str(cats.index[1])
    if a == b:
        b = str(cats.index[1])
    ga = x[g == a].dropna()
    gb = x[g == b].dropna()
    if len(ga) < 2 or len(gb) < 2:
        raise ValueError("Each group needs at least 2 observations.")
    t, p = sc.ttest_ind(ga, gb, equal_var=False, nan_policy="omit")
    explanation = (f"Welch's t-test compares mean '{numeric_col}' between '{a}' (n={len(ga)}, mean={float(ga.mean()):.4g}) "
                   f"and '{b}' (n={len(gb)}, mean={float(gb.mean()):.4g}). t = {float(t):.3f}. " + _explain_p(float(p)))
    code = (f"from scipy import stats\na = df[df[{group_col!r}].astype(str)=={a!r}][{numeric_col!r}]\n"
            f"b = df[df[{group_col!r}].astype(str)=={b!r}][{numeric_col!r}]\nstats.ttest_ind(a, b, equal_var=False)\n")
    return {"test": "welch_ttest", "numeric": numeric_col, "group_col": group_col, "a": a, "b": b,
            "mean_a": _f(float(ga.mean())), "mean_b": _f(float(gb.mean())), "n_a": len(ga), "n_b": len(gb),
            "t_stat": _f(float(t)), "p_value": _f(float(p)), "explanation": explanation, "code": code,
            "groups_available": [str(i) for i in cats.head(20).index.tolist()]}


def chi2(df: pd.DataFrame, col_a: str, col_b: str) -> dict:
    from scipy.stats import chi2_contingency
    if col_a not in df.columns or col_b not in df.columns:
        raise ValueError("Choose two valid columns.")
    ct = pd.crosstab(df[col_a].astype(str), df[col_b].astype(str))
    if ct.shape[0] < 2 or ct.shape[1] < 2:
        raise ValueError("Chi-square needs at least a 2×2 table.")
    if ct.shape[0] * ct.shape[1] > 400:
        raise ValueError("Table too large — reduce categories first.")
    try:
        chi, p, dof, expected = chi2_contingency(ct)
    except Exception as e:
        raise ValueError(f"Chi-square failed: {e}")
    small_expected = bool((expected < 5).sum() > 0.2 * expected.size)
    explanation = (f"Chi-square test of independence between '{col_a}' and '{col_b}'. χ² = {float(chi):.3f}, dof = {int(dof)}. "
                   + _explain_p(float(p))
                   + (" Warning: many expected counts are below 5, so treat this result cautiously." if small_expected else ""))
    code = (f"import pandas as pd\nfrom scipy.stats import chi2_contingency\nct = pd.crosstab(df[{col_a!r}], df[{col_b!r}])\nchi2, p, dof, exp = chi2_contingency(ct)\n")
    return {"test": "chi2", "a": col_a, "b": col_b, "chi2": _f(float(chi)), "dof": int(dof),
            "p_value": _f(float(p)), "table_shape": list(ct.shape), "explanation": explanation, "code": code}


def anova(df: pd.DataFrame, numeric_col: str, group_col: str) -> dict:
    from scipy.stats import f_oneway
    if numeric_col not in df.columns or group_col not in df.columns:
        raise ValueError("Choose a numeric column and a grouping column.")
    x = pd.to_numeric(df[numeric_col], errors="coerce")
    g = df[group_col].astype(str)
    groups = []
    names = []
    for name, idx in g.groupby(g).groups.items():
        vals = x.loc[list(idx)].dropna()
        if len(vals) >= 2:
            groups.append(vals.values)
            names.append(str(name))
        if len(groups) >= 12:
            break
    if len(groups) < 2:
        raise ValueError("ANOVA needs at least 2 groups with ≥2 observations each.")
    try:
        f, p = f_oneway(*groups)
    except Exception as e:
        raise ValueError(f"ANOVA failed: {e}")
    means = [{"group": n, "mean": _f(float(v.mean())), "n": len(v)} for n, v in zip(names, groups)]
    explanation = (f"One-way ANOVA compares mean '{numeric_col}' across {len(groups)} groups. F = {float(f):.3f}. "
                   + _explain_p(float(p)) + " A significant ANOVA says at least one group differs, not which one.")
    code = (f"from scipy.stats import f_oneway\ngroups = [g[{numeric_col!r}].values for _, g in df.groupby({group_col!r})]\nf_oneway(*groups)\n")
    return {"test": "anova", "numeric": numeric_col, "group_col": group_col, "f_stat": _f(float(f)),
            "p_value": _f(float(p)), "groups": means, "explanation": explanation, "code": code}
