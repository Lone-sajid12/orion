"""Professional analysis report builder (markdown + printable HTML)."""
from __future__ import annotations
import pandas as pd
from datetime import datetime
from .profile import dataset_summary
from .quality import quality_report
from .insights import generate_insights


def build_report(df: pd.DataFrame, filename: str, filetype: str, ops_log: list, ml_runs: list, analysis_log: list) -> dict:
    summary = dataset_summary(df, filename, filetype)
    quality = quality_report(df)
    insights = generate_insights(df, max_insights=10)
    # numeric describe
    try:
        desc_html = df.describe(include="all").transpose().to_html(classes="orion-table", border=0)
        desc_md = df.describe(include="all").transpose().to_markdown()
    except Exception:
        desc_html = "<p>Descriptive table unavailable.</p>"
        desc_md = "Descriptive table unavailable."
    # top correlations
    top_corr_md = "Not enough numeric columns."
    try:
        num = df.select_dtypes(include="number")
        if num.shape[1] >= 2:
            c = num.corr(numeric_only=True)
            pairs = []
            cols = c.columns.tolist()
            for i in range(len(cols)):
                for j in range(i + 1, len(cols)):
                    v = c.iloc[i, j]
                    if pd.notna(v):
                        pairs.append((cols[i], cols[j], float(v)))
            pairs.sort(key=lambda t: abs(t[2]), reverse=True)
            lines = [f"| {a} | {b} | {r:.3f} |" for a, b, r in pairs[:8]]
            top_corr_md = "| X | Y | r |\n|---|---|---|\n" + "\n".join(lines)
    except Exception:
        pass

    ops_md = "\n".join(f"- {o.get('label','')} ({o.get('at','')})" for o in ops_log) or "- No cleaning operations applied."
    ml_md = ""
    if ml_runs:
        for run in ml_runs[-3:]:
            ml_md += f"\n### {run.get('target')} ({run.get('task')})\nBest: {run.get('best_name')} — {run.get('best_note','')}\n"
            for r in run.get("results", []):
                if "error" in r:
                    ml_md += f"- {r['name']}: FAILED ({r['error']})\n"
                else:
                    ml_md += f"- {r['name']}: " + ", ".join(f"{k}={v}" for k, v in r["metrics"].items() if v is not None) + "\n"
    else:
        ml_md = "No ML experiments were run for this report."

    issues_md = "\n".join(f"- **[{i['severity']}]** {i['title']} — {i['detail']}" for i in quality["issues"][:20]) or "- No major issues detected."
    insights_md = "\n".join(f"- {ins['title']} — {ins['detail']}" for ins in insights["insights"]) or "- No automatic insights."

    md = f"""# ORION Analysis Report
**Dataset:** {filename} ({filetype}) · **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Analyst:** Sajid Jamal · *Turn Data Into Decisions.*

## 1. Dataset overview
- Rows: **{summary['rows']:,}** · Columns: **{summary['columns']}**
- Numeric: {len(summary['numeric_columns'])} ({', '.join(summary['numeric_columns'][:8]) or '—'})
- Categorical: {len(summary['categorical_columns'])} ({', '.join(summary['categorical_columns'][:8]) or '—'})
- Datetime: {len(summary['datetime_columns'])} ({', '.join(summary['datetime_columns'][:5]) or '—'})
- Missing cells: {summary['missing_cells']:,} ({summary['missing_pct']}%) · Duplicate rows: {summary['duplicate_rows']:,}
- Memory: ~{summary['memory_mb']} MB · Quality score: **{quality['score']}/100**

## 2. Data-quality findings
{issues_md}

## 3. Cleaning operations applied
{ops_md}

## 4. Descriptive statistics
{desc_md}

## 5. Strongest correlations
{top_corr_md}

## 6. Key insights (heuristic — verify before acting)
{insights_md}

## 7. Machine learning
{ml_md}

## 8. Limitations
- Analysis is limited to the uploaded snapshot; sampling bias and collection methods are unknown.
- Correlation does not imply causation; hypothesis tests assume roughly independent observations.
- ML scores are estimates on a single train/test split unless cross-validation was inspected.

## 9. Recommendations
- Resolve high-severity quality issues first (empty columns, excessive missingness, duplicates).
- Validate surprising insights with a chart in Explore/Visualize before reporting them.
- For modelling, prefer the simplest model within noise of the best, and test on genuinely new data.

---
*Generated locally by ORION. Your data never left this computer.*
"""
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>ORION Report — {filename}</title>
<style>
body{{font-family:Georgia,'Times New Roman',serif;background:#F3EFE6;color:#252522;max-width:880px;margin:0 auto;padding:40px 28px}}
h1{{font-size:30px;margin-bottom:4px}}h2{{font-size:19px;margin-top:30px;border-bottom:2px solid #D9D4C8;padding-bottom:6px}}h3{{font-size:15px}}
.meta{{color:#68665E;font-size:13px}}.orion-table{{width:100%;border-collapse:collapse;font-size:12px;background:#FAF8F2}}
.orion-table th,.orion-table td{{border:1px solid #D9D4C8;padding:6px 8px;text-align:left}}
.card{{background:#FAF8F2;border:1px solid #D9D4C8;padding:14px 16px;margin:10px 0}}
ul{{line-height:1.6}}@media print{{body{{background:#fff}}}}
</style></head><body>
<h1>ORION Analysis Report</h1>
<div class="meta">Dataset: <b>{filename}</b> · Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · Analyst: Sajid Jamal · <i>Turn Data Into Decisions.</i></div>
<h2>1 · Dataset overview</h2>
<div class="card">Rows <b>{summary['rows']:,}</b> · Columns <b>{summary['columns']}</b> · Quality score <b>{quality['score']}/100</b><br>
Numeric: {', '.join(summary['numeric_columns'][:10]) or '—'}<br>Categorical: {', '.join(summary['categorical_columns'][:10]) or '—'}<br>
Datetime: {', '.join(summary['datetime_columns'][:6]) or '—'}<br>Missing cells: {summary['missing_cells']:,} ({summary['missing_pct']}%) · Duplicates: {summary['duplicate_rows']:,}</div>
<h2>2 · Data-quality findings</h2>
<ul>{''.join(f"<li><b>[{i['severity']}]</b> {i['title']}</li>" for i in quality['issues'][:20]) or '<li>No major issues.</li>'}</ul>
<h2>3 · Cleaning operations</h2>
<ul>{''.join(f"<li>{o.get('label','')}</li>" for o in ops_log) or '<li>No cleaning operations applied.</li>'}</ul>
<h2>4 · Descriptive statistics</h2>
{desc_html}
<h2>5 · Key insights</h2>
<ul>{''.join(f"<li><b>{ins['title']}</b><br><span class='meta'>{ins['detail']}</span></li>" for ins in insights['insights'])}</ul>
<h2>6 · Limitations &amp; next steps</h2>
<div class="card">Correlation is not causation. Validate insights visually, fix high-severity quality flags first, and test ML models on genuinely new data before trusting them.</div>
<div class="meta" style="margin-top:24px">Generated locally by ORION · No database · No cloud · Your data stayed on this computer.</div>
</body></html>"""
    return {"markdown": md, "html": html, "summary": summary, "quality_score": quality["score"]}
