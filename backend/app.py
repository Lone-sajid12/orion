"""ORION backend — FastAPI, local-first, no database, no API keys."""
from __future__ import annotations
import io
import traceback
from typing import Any, Optional
import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from orion_engine.state import store
from orion_engine.loader import load_table, LoadError
from orion_engine.profile import dataset_summary, full_profile, column_profile, preview
from orion_engine.quality import quality_report
from orion_engine.cleaning import apply_operation
from orion_engine.eda import univariate, correlation_matrix, build_chart, bivariate
from orion_engine.stats import descriptive, correlation, confidence_interval, ttest, chi2, anova
from orion_engine.insights import generate_insights
from orion_engine.ml import suggest_targets, train_models, predict_with_run
from orion_engine.nl import answer_question, ollama_status, ollama_explain
from orion_engine.report import build_report
from orion_engine.dtypes import classify_columns

app = FastAPI(title="ORION API", version="1.0.0",
              description="Local-first data workstation engine. No DB, no cloud, no API keys.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_data():
    if not store.has_data():
        raise HTTPException(status_code=400, detail="No dataset loaded. Import a CSV or Excel file first.")
    return store.get_df()


@app.exception_handler(Exception)
async def generic_handler(request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"ok": False, "error": exc.detail})
    # Never leak raw stack traces to normal users; log server-side
    print("ORION error:", traceback.format_exc()[-2000:])
    msg = str(exc) if len(str(exc)) < 300 else "An unexpected error occurred while processing your request."
    return JSONResponse(status_code=500, content={"ok": False, "error": msg})


@app.get("/api/health")
def health():
    return {"ok": True, "has_data": store.has_data(),
            "filename": store.current.filename if store.current else None}


# ---------- import ----------

@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    try:
        content = await file.read()
        df, ftype = load_table(file.filename or "dataset", content)
        store.set_dataset(df, file.filename or "dataset", ftype)
        assert store.current is not None
        summary = dataset_summary(df, store.current.filename, ftype)
        return {"ok": True, "summary": summary}
    except LoadError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load file: {e}")


@app.post("/api/load-sample")
def load_sample():
    """Load bundled sample dataset for onboarding (clearly labelled)."""
    import os
    import pandas as pd
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "sample_data", "orion_sample_sales.csv")
    path = os.path.abspath(path)
    try:
        df = pd.read_csv(path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sample data unavailable: {e}")
    store.set_dataset(df, "orion_sample_sales.csv (Sample Dataset)", "csv")
    assert store.current is not None
    summary = dataset_summary(df, store.current.filename, "csv")
    return {"ok": True, "summary": summary, "sample": True}


# ---------- dataset ----------

@app.get("/api/dataset/summary")
def api_summary():
    df = _require_data()
    assert store.current is not None
    roles = classify_columns(df)
    return {
        "ok": True,
        "summary": dataset_summary(df, store.current.filename, store.current.filetype),
        "quality": {"ok": True, **quality_report(df)},
        "columns": list(df.columns),
        "roles": roles,
        "ops": store.current.ops_log,
        "can_undo": len(store.current.history) > 0,
        "analysis_log": store.current.analysis_log[-12:][::-1],
    }


@app.get("/api/dataset/preview")
def api_preview(page: int = 1, page_size: int = 25, search: str = "", sort_col: str = "", sort_dir: str = "asc"):
    df = _require_data()
    return {"ok": True, **preview(df, page, page_size, search, sort_col, sort_dir)}


@app.get("/api/dataset/profile")
def api_profile():
    df = _require_data()
    return {"ok": True, **full_profile(df)}


@app.get("/api/dataset/column")
def api_column(name: str):
    df = _require_data()
    try:
        return {"ok": True, "profile": column_profile(df, name)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/dataset/columns")
def api_columns():
    df = _require_data()
    roles = classify_columns(df)
    return {"ok": True, "columns": list(df.columns), "roles": roles,
            "numeric": [c for c, r in roles.items() if r == "numeric"],
            "categorical": [c for c, r in roles.items() if r in ("categorical", "boolean")],
            "datetime": [c for c, r in roles.items() if r == "datetime"]}


# ---------- quality ----------

@app.get("/api/quality")
def api_quality():
    df = _require_data()
    return {"ok": True, **quality_report(df)}


# ---------- cleaning ----------

class CleanRequest(BaseModel):
    op: str
    column: Optional[str] = None
    columns: Optional[Any] = None
    strategy: Optional[str] = None
    value: Optional[Any] = None
    old: Optional[str] = None
    new: Optional[str] = None
    dtype: Optional[str] = None
    case: Optional[str] = None
    method: Optional[str] = None


@app.post("/api/clean/apply")
def api_clean_apply(req: CleanRequest):
    df = _require_data()
    op = {k: v for k, v in req.model_dump().items() if v is not None}
    try:
        new_df, code, label = apply_operation(df, op)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    store.apply_df(new_df, label, op, code)
    assert store.current is not None
    summary = dataset_summary(new_df, store.current.filename, store.current.filetype)
    return {"ok": True, "message": label, "code": code, "summary": summary,
            "can_undo": len(store.current.history) > 0}


@app.post("/api/clean/undo")
def api_clean_undo():
    label = store.undo()
    if label is None:
        raise HTTPException(status_code=400, detail="Nothing to undo.")
    df = _require_data()
    assert store.current is not None
    return {"ok": True, "message": f"Undid: {label}",
            "summary": dataset_summary(df, store.current.filename, store.current.filetype),
            "can_undo": len(store.current.history) > 0}


@app.post("/api/clean/reset")
def api_clean_reset():
    store.reset_to_original()
    df = _require_data()
    assert store.current is not None
    return {"ok": True, "summary": dataset_summary(df, store.current.filename, store.current.filetype)}


# ---------- EDA / visualize ----------

@app.get("/api/eda/univariate")
def api_univariate(col: str):
    df = _require_data()
    try:
        res = univariate(df, col)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    store.log_analysis("eda", f"Univariate analysis of '{col}'")
    return {"ok": True, **res}


@app.get("/api/eda/correlation")
def api_corr(method: str = "pearson"):
    df = _require_data()
    try:
        res = correlation_matrix(df, method)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    store.log_analysis("eda", f"Correlation matrix ({method})")
    return {"ok": True, **res}


@app.post("/api/eda/chart")
def api_chart(spec: dict = Body(...)):
    df = _require_data()
    try:
        res = build_chart(df, spec)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    store.log_analysis("visualize", f"Chart: {spec.get('type')} ({spec.get('x') or spec.get('y') or ''})")
    return {"ok": True, "chart": res}


@app.get("/api/eda/bivariate")
def api_bivariate(x: str, y: str):
    df = _require_data()
    try:
        res = bivariate(df, x, y)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    store.log_analysis("eda", f"Bivariate: '{x}' vs '{y}'")
    return {"ok": True, **res}


# ---------- insights ----------

@app.get("/api/insights")
def api_insights():
    df = _require_data()
    res = generate_insights(df)
    store.log_analysis("insights", f"Generated {res['count']} insights")
    return {"ok": True, **res}


# ---------- stats ----------

@app.post("/api/stats/descriptive")
def api_descriptive(body: dict = Body(default={})):
    df = _require_data()
    try:
        res = descriptive(df, body.get("columns"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    store.log_analysis("stats", "Descriptive statistics")
    return {"ok": True, **res}


@app.post("/api/stats/correlation")
def api_stat_corr(body: dict = Body(...)):
    df = _require_data()
    try:
        res = correlation(df, body.get("x", ""), body.get("y", ""), body.get("method", "pearson"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    store.log_analysis("stats", f"Correlation: {body.get('x')} ↔ {body.get('y')}")
    return {"ok": True, **res}


@app.post("/api/stats/ci")
def api_ci(body: dict = Body(...)):
    df = _require_data()
    try:
        res = confidence_interval(df, body.get("column", ""), float(body.get("level", 0.95)))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, **res}


@app.post("/api/stats/ttest")
def api_ttest(body: dict = Body(...)):
    df = _require_data()
    try:
        res = ttest(df, body.get("numeric", ""), body.get("group", ""), body.get("a"), body.get("b"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    store.log_analysis("stats", f"t-test: {body.get('numeric')} by {body.get('group')}")
    return {"ok": True, **res}


@app.post("/api/stats/chi2")
def api_chi2(body: dict = Body(...)):
    df = _require_data()
    try:
        res = chi2(df, body.get("a", ""), body.get("b", ""))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    store.log_analysis("stats", f"Chi-square: {body.get('a')} × {body.get('b')}")
    return {"ok": True, **res}


@app.post("/api/stats/anova")
def api_anova(body: dict = Body(...)):
    df = _require_data()
    try:
        res = anova(df, body.get("numeric", ""), body.get("group", ""))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    store.log_analysis("stats", f"ANOVA: {body.get('numeric')} by {body.get('group')}")
    return {"ok": True, **res}


# ---------- ML ----------

@app.get("/api/ml/targets")
def api_targets():
    df = _require_data()
    return {"ok": True, **suggest_targets(df)}


@app.post("/api/ml/train")
def api_train(body: dict = Body(...)):
    df = _require_data()
    try:
        res = train_models(df, body.get("target", ""), body.get("task", ""),
                           body.get("models"), float(body.get("test_size", 0.2)),
                           int(body.get("cv", 5)), body.get("exclude", []))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    assert store.current is not None
    store.current.ml_runs.append({k: v for k, v in res.items() if k != "code"})
    store.current.code_log.append({"label": f"ML train: {res['target']} ({res['task']})", "code": res["code"], "at": "now"})
    store.log_analysis("ml", f"Trained {len(res['results'])} model(s) → {res['target']}")
    return {"ok": True, **res}


@app.post("/api/ml/predict")
def api_predict(body: dict = Body(...)):
    try:
        res = predict_with_run(body.get("run_id", ""), body.get("values", {}))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, **res}


# ---------- NL ----------

@app.post("/api/ask")
def api_ask(body: dict = Body(...)):
    df = _require_data()
    try:
        res = answer_question(df, body.get("question", ""))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    store.log_analysis("ask", f"Q: {body.get('question','')[:60]}")
    return {"ok": True, **res}


@app.get("/api/ai/status")
def api_ai_status():
    return {"ok": True, **ollama_status()}


@app.post("/api/ai/explain")
def api_ai_explain(body: dict = Body(...)):
    res = ollama_explain(body.get("prompt", ""), body.get("model", ""))
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error", "Local AI unavailable"))
    return {"ok": True, **res}


# ---------- report ----------

@app.get("/api/report")
def api_report(format: str = "json"):
    df = _require_data()
    assert store.current is not None
    rep = build_report(df, store.current.filename, store.current.filetype,
                       store.current.ops_log, store.current.ml_runs, store.current.analysis_log)
    store.log_analysis("report", "Generated analysis report")
    if format == "html":
        return HTMLResponse(content=rep["html"])
    if format == "markdown":
        return PlainTextResponse(content=rep["markdown"])
    return {"ok": True, **rep}


@app.get("/api/code-log")
def api_code_log():
    if not store.has_data() or store.current is None:
        return {"ok": True, "entries": []}
    return {"ok": True, "entries": store.current.code_log[-20:][::-1]}


@app.get("/api")
def api_root():
    return {"name": "ORION", "tagline": "Turn Data Into Decisions.", "docs": "/docs"}


# ---- production: serve the built React frontend if present (single-process mode) ----
_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
if os.path.isdir(_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    def serve_index():
        return FileResponse(os.path.join(_DIST, "index.html"))

    @app.get("/{path:path}", include_in_schema=False)
    def serve_spa(path: str):
        # API + docs routes are matched first; everything else falls back to the SPA
        candidate = os.path.join(_DIST, path)
        if path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(_DIST, "index.html"))
else:

    @app.get("/", include_in_schema=False)
    def root():
        return {"name": "ORION", "tagline": "Turn Data Into Decisions.", "docs": "/docs",
                "frontend": "Run the React dev server (cd frontend && npm run dev) or build it (npm run build) for single-process mode."}
