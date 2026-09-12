# ORION — Turn Data Into Decisions.

A **local-first, privacy-conscious Data Analysis & Data Science workstation** built for
**Sajid Jamal** (Computer Science student · Data Analysis → Data Science → AI/ML).

Import real CSV/Excel datasets and profile, clean, visualize, statistically test, model,
and report on them — with every step showing the **Python code behind it** so you learn
while you analyze.

> **No external API key is required for core functionality.**
> **No database is required.**

---

## Screenshots

> Placeholder — capture after first run:
>
> - `docs/screenshot-dashboard.png` — dataset-aware dashboard
> - `docs/screenshot-quality.png` — Quality Center with detected issues
> - `docs/screenshot-visualize.png` — chart builder with a live Plotly chart
> - `docs/screenshot-ml.png` — model comparison + prediction workspace

---

## Features

| Area | What ORION does (all on your real data) |
|---|---|
| **Dashboard** | Dataset-aware overview: shape, types, missingness, duplicates, quality score, recent analysis, quick actions |
| **Datasets** | Drag-&-drop CSV/XLSX/XLS import, encoding-tolerant parsing, paginated searchable preview, full column profiles |
| **Data Quality** | Auto-detects missing data, duplicates, constant/empty columns, outliers, mixed types, whitespace & case issues, high-cardinality columns — with explanations and one-click reversible fixes |
| **Cleaning** | Fill/drop/rename/convert/trim/encode/scale/cap with **Undo**, session history, and generated pandas code. Original file never touched |
| **Explore (EDA)** | Univariate distributions, bivariate analysis with auto-recommended charts, Pearson/Spearman/Kendall correlation matrices |
| **Visualize** | Chart builder: bar, line, area, histogram, box, scatter, pie/donut (guarded to ≤12 categories), correlation heatmap, time series — PNG export built in |
| **Statistics Lab** | Descriptives, correlation with p-values, confidence intervals, Welch's t-test, chi-square, ANOVA — each with plain-language interpretation |
| **Insights** | Heuristic findings: strongest correlations, skew, dominant categories, group gaps, trends, outliers. Association only — never claims causation |
| **Ask Data** | Natural-language questions (“average revenue?”, “strongest correlations?”, “unusual records?”) compiled to real pandas operations |
| **ML Lab** | Target suggestions (you choose), regression & classification, imputation + scaling + one-hot pipelines, train/test split, 5-fold CV, MAE/MSE/RMSE/R², accuracy/precision/recall/F1/confusion matrix/ROC-AUC, model comparison, feature importance, prediction workspace |
| **Reports** | Professional Markdown + printable HTML report: overview, quality, cleaning log, stats, insights, ML, limitations, recommendations |
| **Code journal** | “View Python Code” everywhere — copy or download `.py` to learn the translation from clicks to code |
| **Local AI (optional)** | Detects **Ollama** on `localhost:11434` if you install it; core analysis never depends on it |

---

## Architecture

```
orion/
├── backend/                    # FastAPI engine (Python)
│   ├── app.py                  # 30+ REST endpoints, serves built frontend in --single mode
│   ├── requirements.txt        # pinned deps
│   └── orion_engine/
│       ├── state.py            # in-memory session (no database, by design)
│       ├── loader.py           # CSV/Excel ingestion + validation
│       ├── dtypes.py           # column-role detection (numeric/categorical/datetime/…)
│       ├── profile.py          # summaries, column profiles, paginated preview
│       ├── quality.py          # quality checks + 0–100 score
│       ├── cleaning.py         # reversible transforms + pandas codegen
│       ├── eda.py              # univariate/bivariate/correlation/chart specs
│       ├── stats.py            # descriptives, CI, t-test, chi², ANOVA + explanations
│       ├── insights.py         # rule-based findings (association, never causation)
│       ├── ml.py               # sklearn pipelines, comparison, prediction
│       ├── nl.py               # NL → pandas compiler + optional Ollama probe
│       └── report.py           # Markdown + HTML report builder
├── frontend/                   # React + TypeScript + Tailwind + Plotly
│   └── src/
│       ├── components/         # Sidebar, PlotView, ui kit (cards, code viewer, …)
│       ├── pages/              # 11 workspace views (Dashboard … Settings)
│       └── lib/api.ts          # typed API client
├── sample_data/
│   └── orion_sample_sales.csv  # labelled sample (600 rows) for onboarding
├── scripts/make_sample.py      # regenerates the sample deterministically
├── start.sh / start.bat        # one-command launchers
└── README.md
```

**Design principles**

- **Two modes**: *Core Mode* (zero AI, full analysis) and *Local AI Mode* (optional Ollama explanations).
- **Deterministic first**: pandas/NumPy/SciPy/sklearn do the analysis; no LLM in the critical path.
- **No database**: datasets live in server-process memory; only UI prefs touch `localStorage`.
- **Honest errors**: invalid files, empty data, unsuitable targets, and failed tests return clear messages — never stack traces, never fake numbers.

---

## Technology stack

- **Engine**: Python 3.10+, FastAPI, uvicorn, pandas, NumPy, SciPy, scikit-learn, openpyxl, xlrd, tabulate
- **Interface**: React 18, TypeScript, Vite, Tailwind CSS, Plotly
- **Optional AI**: Ollama (any local model, e.g. `llama3.1`) — detected automatically, never required

---

## Installation

**Prerequisites**: Python 3.10+ and Node.js 18+.

```bash
# 1. Clone / download this folder, then:
cd orion

# 2a. Easiest — one command (installs deps on first run):
./start.sh                 # macOS / Linux
start.bat                  # Windows (double-click)

# 2b. Or manually:
python3 -m pip install -r backend/requirements.txt
cd frontend && npm install
```

## Usage

```bash
# Development (two servers with hot reload)
./start.sh
# → open http://localhost:5173   (engine API at http://localhost:8000)

# Production single-process mode (builds UI, serves all from :8000)
./start.sh --single
# → open http://localhost:8000
```

**First analysis (5 minutes)**

1. Open ORION → **Import Dataset** (or *Try Sample Dataset*).
2. **Dashboard** confirms real row/column counts → **Datasets** to profile columns.
3. **Data Quality**: review issues, apply a fix, press **Undo**, re-apply.
4. **Explore** a distribution and a correlation matrix.
5. **Visualize** a bar + a time-series chart.
6. **Statistics**: run a t-test; read the plain-language verdict.
7. **Ask Data**: “What are the strongest correlations?”
8. **Machine Learning**: pick a suggested target, train, compare, predict.
9. **Reports**: download the HTML report for your portfolio.

## Supported datasets

- `.csv` (encoding-tolerant: UTF-8, UTF-8-SIG, Latin-1, CP1252; delimiter-sniffed)
- `.xlsx` / `.xlsm` / `.xls` (first sheet)
- Guards: 250 MB file cap, 1M-row / 500-column safety limits, empty-file and garbage detection
- Large data stays responsive via paginated previews, downsampled scatter rendering, and capped matrices

## Local AI setup (optional)

ORION is complete without this. To add local explanations:

```bash
# 1. Install Ollama from https://ollama.com
# 2. Pull a model and serve it:
ollama pull llama3.1
ollama serve
# 3. Open ORION → Settings → Local AI shows “Connected”.
```

ORION only ever calls `localhost:11434`. No cloud, no keys, no dataset leaves your machine.

## Verification (test report)

End-to-end suite run against the live engine — **46/46 passing**:

- **Import**: CSV, Excel (xlsx round-trip), latin-1 encoding, `;`/tab delimiters, single-column files;
  invalid extension, empty file, header-only file, and binary junk all rejected with clear messages.
- **Quality/cleaning**: score + issue detection, fill/rename/convert/trim/encode/scale/cap, Undo, reset;
  invalid columns/operations rejected.
- **EDA/visuals**: univariate (numeric + categorical), Pearson/Spearman/Kendall matrices,
  bar/line/area/histogram/box/scatter/pie/heatmap charts, bivariate auto-recommendation;
  pie guarded against high-cardinality columns.
- **Statistics**: descriptives, correlation + p-value, confidence intervals, Welch's t-test,
  chi-square, ANOVA — each with plain-language verdicts.
- **NL questions**: averages, missingness, correlations, trends, outliers, shape — all computed from real data.
- **ML**: target suggestions, regression (Linear/RF/GBM) and classification (LogReg/Tree/RF/KNN/GBM)
  with train/test split, CV, full metric sets, confusion matrices, feature importance, and new predictions;
  datetime targets, tiny frames, and single-class targets rejected with guidance.
- **Perf**: 50k-row frame uploads in ~0.2s; scatters downsampled to ≤5,000 points; ML auto-samples
  beyond 25k rows with an honest on-screen note (verified: no OOM on a 2GB machine).
- **Production**: `npm run build` bundles the UI to `dist/` (Plotly ships as a local static asset so builds
  stay light and the app works fully offline); `./start.sh --single` serves UI + API from one process.

## Privacy

> “Your datasets stay on your computer unless you explicitly configure an external service.”

- No database, no accounts, no analytics, no telemetry.
- Uploads go to the local engine process memory only (same machine).
- Original files are never modified; cleaning works on an in-memory copy with Undo.

## Limitations

- Single-user, single-dataset session (importing replaces the working copy).
- In-memory engine: restarting the backend clears the session (export reports/code first).
- Excel reads the first sheet only; very wide tables (>500 cols) are rejected with guidance.
- Charts downsample scatters beyond ~5,000 points for interactivity (statistics always use full data).
- Heuristic insights are starting points, not conclusions — verify with charts and tests.

## Future improvements

- Multi-dataset tabs + session save/load to local files (Parquet snapshots).
- Date-part feature engineering, group-by aggregation builder, pivot tables.
- Saved chart gallery, dashboard pinning, scheduled report export.
- Opt-in local-LLM narrative summaries grounded strictly in computed statistics.
- One-click installers (PyInstaller/Electron) for fully offline use.

## Learning objectives (for Sajid)

Working through ORION end-to-end practices the real Data Analysis → Data Science → AI/ML ladder:

1. **Data Analysis**: profiling, cleaning, EDA, visualization, reporting.
2. **Data Science**: distributions, correlation vs causation, hypothesis testing, confidence intervals.
3. **AI/ML**: preprocessing pipelines, train/test discipline, cross-validation, metric selection (R² vs F1), leakage awareness, honest model comparison.

Every screen links actions to **“View Python Code”** — read it, run it in your own notebooks, and make it yours.

---

*ORION · Turn Data Into Decisions. · Created for Sajid Jamal · Local-first: no database, no API keys.*
