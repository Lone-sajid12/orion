"""ML lab: target suggestion, training, comparison, prediction. Deterministic sklearn."""
from __future__ import annotations
import io
import math
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold, KFold
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, GradientBoostingRegressor, GradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import (mean_absolute_error, mean_squared_error, r2_score, accuracy_score,
                             precision_score, recall_score, f1_score, confusion_matrix, roc_auc_score)
from .dtypes import classify_columns


def _f(v):
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 4)
    except Exception:
        return None


REG_MODELS = {
    "linear": ("Linear Regression", LinearRegression()),
    "random_forest": ("Random Forest", RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)),
    "gradient_boosting": ("Gradient Boosting", GradientBoostingRegressor(random_state=42)),
}
CLF_MODELS = {
    "logistic": ("Logistic Regression", LogisticRegression(max_iter=2000)),
    "decision_tree": ("Decision Tree", DecisionTreeClassifier(random_state=42)),
    "random_forest": ("Random Forest", RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)),
    "knn": ("K-Nearest Neighbors", KNeighborsClassifier()),
    "gradient_boosting": ("Gradient Boosting", GradientBoostingClassifier(random_state=42)),
}


def suggest_targets(df: pd.DataFrame) -> dict:
    roles = classify_columns(df)
    n = len(df)
    suggestions = []
    for col, role in roles.items():
        s = df[col]
        nunique = int(s.nunique(dropna=True))
        missing_pct = 100 * int(s.isna().sum()) / n if n else 0
        if role == "numeric":
            # continuous? many unique values
            if nunique < 5:
                reason = f"Numeric with only {nunique} distinct values — better suited as a feature or classification target, not regression."
                task = "classification?"
                suitable = False
                score = 0.2
            elif missing_pct > 30:
                reason = f"Continuous values but {missing_pct:.0f}% missing — would shrink training data."
                task = "regression"
                suitable = False
                score = 0.3
            else:
                reason = "Continuous numeric values with good variation — suitable for regression."
                task = "regression"
                suitable = True
                score = 0.9 if nunique > 20 else 0.7
            suggestions.append({"column": col, "task": task, "suitable": suitable, "reason": reason,
                                "unique": nunique, "missing_pct": round(missing_pct, 1), "score": score})
        elif role in ("categorical", "boolean"):
            if nunique < 2:
                suggestions.append({"column": col, "task": "classification", "suitable": False,
                                    "reason": "Only one category — nothing to predict.", "unique": nunique,
                                    "missing_pct": round(missing_pct, 1), "score": 0.0})
            elif nunique > 20:
                suggestions.append({"column": col, "task": "classification", "suitable": False,
                                    "reason": f"{nunique} classes is too many for basic classification.",
                                    "unique": nunique, "missing_pct": round(missing_pct, 1), "score": 0.2})
            elif nunique == n:
                suggestions.append({"column": col, "task": "classification", "suitable": False,
                                    "reason": "Every value is unique — looks like an identifier, not a target.",
                                    "unique": nunique, "missing_pct": round(missing_pct, 1), "score": 0.0})
            else:
                vc = s.value_counts(dropna=True, normalize=True)
                top_pct = float(vc.iloc[0]) * 100
                note = f" Imbalanced: top class is {top_pct:.0f}% — use stratified split and F1." if top_pct >= 70 else ""
                suggestions.append({"column": col, "task": "classification", "suitable": True,
                                    "reason": f"{nunique} classes with enough examples per class — suitable for classification." + note,
                                    "unique": nunique, "missing_pct": round(missing_pct, 1),
                                    "score": 0.85, "classes": [str(c)[:40] for c in s.dropna().unique().tolist()[:10]]})
        else:
            suggestions.append({"column": col, "task": "—", "suitable": False,
                                "reason": "Datetime/free-text columns are not direct targets.",
                                "unique": nunique, "missing_pct": round(missing_pct, 1), "score": 0.0})
    suggestions.sort(key=lambda d: d["score"], reverse=True)
    return {"suggestions": suggestions}


def _build_preprocessor(X: pd.DataFrame):
    num_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = [c for c in X.columns if c not in num_cols]
    # cap cardinality: group rare? For robustness, OneHot with max_categories
    try:
        ohe = OneHotEncoder(handle_unknown="ignore", max_categories=30)
    except TypeError:
        ohe = OneHotEncoder(handle_unknown="ignore")
    num_pipe = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())])
    cat_pipe = Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", ohe)])
    pre = ColumnTransformer([("num", num_pipe, num_cols), ("cat", cat_pipe, cat_cols)], remainder="drop")
    return pre, num_cols, cat_cols


MAX_TRAIN_ROWS = 25000  # memory guard: larger frames are sampled (reported honestly)


def _cap_estimator(key: str, est, n: int):
    """Downsize expensive ensembles on large data to bound memory/time."""
    try:
        from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
        if n > 10000 and isinstance(est, (RandomForestRegressor, RandomForestClassifier)):
            est.set_params(n_estimators=100)
    except Exception:
        pass
    return est


def train_models(df: pd.DataFrame, target: str, task: str, models: list[str] | None = None,
                 test_size: float = 0.2, cv: int = 5, exclude: list[str] | None = None) -> dict:
    if target not in df.columns:
        raise ValueError(f"Target '{target}' not found.")
    if task not in ("regression", "classification"):
        raise ValueError("task must be 'regression' or 'classification'.")
    # Guard: datetime / free-text columns are not valid targets
    try:
        _roles = classify_columns(df)
        _trole = _roles.get(target, "")
        if _trole == "datetime":
            raise ValueError(f"'{target}' is a datetime column, which cannot be a prediction target. Pick a numeric column for regression or a categorical column for classification.")
        if _trole == "text":
            raise ValueError(f"'{target}' looks like free text / unique identifiers, which cannot be a prediction target.")
    except ValueError:
        raise
    except Exception:
        pass
    exclude = exclude or []
    feature_cols = [c for c in df.columns if c != target and c not in exclude]
    if not feature_cols:
        raise ValueError("No feature columns left after excluding the target.")
    # drop datetime cols from features? convert to ordinal? Simplest: drop datetime + high-card text handled by OHE cap
    work = df[feature_cols + [target]].copy()
    # drop rows where target missing
    before = len(work)
    work = work[work[target].notna()]
    dropped_target_na = before - len(work)
    if len(work) < 20:
        raise ValueError(f"Only {len(work)} usable rows after dropping missing targets — need at least 20.")
    # memory guard: sample very large frames (reported honestly in the result)
    sampling_note = None
    if len(work) > MAX_TRAIN_ROWS:
        if task == "classification":
            try:
                work = work.groupby(work[target].astype(str), group_keys=False).apply(
                    lambda g: g.sample(n=max(1, int(len(g) / len(work) * MAX_TRAIN_ROWS)), random_state=42))
                # top up / trim to exact cap
                if len(work) > MAX_TRAIN_ROWS:
                    work = work.sample(n=MAX_TRAIN_ROWS, random_state=42)
            except Exception:
                work = work.sample(n=MAX_TRAIN_ROWS, random_state=42)
        else:
            work = work.sample(n=MAX_TRAIN_ROWS, random_state=42)
        sampling_note = (f"Training on a {MAX_TRAIN_ROWS:,}-row sample of {before:,} usable rows "
                         f"(memory guard; sample is stratified by target for classification). Metrics estimate full-data performance.")
    # adaptive CV folds on large data
    eff_cv = min(cv, 3) if len(work) > 10000 else min(cv, 5)
    y_raw = work[target]
    X_raw = work[feature_cols].copy()
    # convert datetime features to numeric ordinal
    for c in X_raw.columns:
        if pd.api.types.is_datetime64_any_dtype(X_raw[c]):
            try:
                X_raw[c] = pd.to_datetime(X_raw[c]).map(lambda x: x.toordinal() if pd.notna(x) else np.nan)
            except Exception:
                X_raw = X_raw.drop(columns=[c])
    # drop all-NA feature cols
    allna = [c for c in X_raw.columns if X_raw[c].isna().all()]
    if allna:
        X_raw = X_raw.drop(columns=allna)
    if X_raw.shape[1] == 0:
        raise ValueError("No usable feature columns (all empty or invalid).")

    if task == "regression":
        y = pd.to_numeric(y_raw, errors="coerce")
        m = y.notna()
        X_raw, y = X_raw[m], y[m]
        if len(y) < 20:
            raise ValueError("Target has too few valid numeric values for regression.")
        if y.nunique() < 5:
            raise ValueError("Regression target needs more distinct values (got fewer than 5).")
        registry = REG_MODELS
        wanted = models or ["linear", "random_forest"]
    else:
        y = y_raw.astype(str)
        # encode labels
        classes = sorted(y.unique().tolist())
        if len(classes) < 2:
            raise ValueError("Classification target needs at least 2 classes.")
        if len(classes) > 20:
            raise ValueError(f"Target has {len(classes)} classes — too many for basic classification.")
        # min class size
        min_count = int(y.value_counts().min())
        if min_count < 2:
            raise ValueError("Every class needs at least 2 examples.")
        registry = CLF_MODELS
        wanted = models or ["logistic", "random_forest"]
    wanted = [w for w in wanted if w in registry]
    if not wanted:
        raise ValueError("No valid models selected.")

    if not 0.1 <= test_size <= 0.4:
        raise ValueError("Test size must be between 0.1 and 0.4.")
    strat = y if task == "classification" else None
    try:
        X_train, X_test, y_train, y_test = train_test_split(X_raw, y, test_size=test_size, random_state=42, stratify=strat)
    except ValueError:
        X_train, X_test, y_train, y_test = train_test_split(X_raw, y, test_size=test_size, random_state=42)

    pre, num_cols, cat_cols = _build_preprocessor(X_train)
    results = []
    fitted: dict[str, Pipeline] = {}
    for key in wanted:
        label, est = registry[key]
        est = _cap_estimator(key, est, len(X_raw))
        pipe = Pipeline([("pre", pre), ("model", est)])
        try:
            pipe.fit(X_train, y_train)
        except Exception as e:
            results.append({"key": key, "name": label, "error": f"Training failed: {e}"})
            continue
        try:
            pred = pipe.predict(X_test)
        except Exception as e:
            results.append({"key": key, "name": label, "error": f"Prediction failed: {e}"})
            continue
        fitted[key] = pipe
        if task == "regression":
            mae = mean_absolute_error(y_test, pred)
            mse = mean_squared_error(y_test, pred)
            rmse = float(np.sqrt(mse))
            r2 = r2_score(y_test, pred)
            # cv
            try:
                cv_scores = cross_val_score(pipe, X_raw, y, cv=KFold(n_splits=eff_cv, shuffle=True, random_state=42), scoring="r2")
                cv_mean, cv_std = float(np.mean(cv_scores)), float(np.std(cv_scores))
            except Exception:
                cv_mean, cv_std = None, None
            results.append({"key": key, "name": label, "metrics": {
                "mae": _f(mae), "mse": _f(mse), "rmse": _f(rmse), "r2": _f(r2),
                "cv_r2_mean": _f(cv_mean), "cv_r2_std": _f(cv_std)}, "n_train": len(X_train), "n_test": len(X_test)})
        else:
            acc = accuracy_score(y_test, pred)
            prec = precision_score(y_test, pred, average="weighted", zero_division=0)
            rec = recall_score(y_test, pred, average="weighted", zero_division=0)
            f1 = f1_score(y_test, pred, average="weighted", zero_division=0)
            cm = confusion_matrix(y_test, pred, labels=sorted(y.unique().tolist()))
            roc = None
            try:
                if len(np.unique(y_test)) == 2 and hasattr(pipe, "predict_proba"):
                    proba = pipe.predict_proba(X_test)
                    # align positive class
                    roc = roc_auc_score(pd.factorize(y_test)[0], proba[:, 1] if proba.shape[1] == 2 else proba.max(axis=1))
            except Exception:
                roc = None
            try:
                cv_scores = cross_val_score(pipe, X_raw, y, cv=StratifiedKFold(n_splits=eff_cv, shuffle=True, random_state=42), scoring="f1_weighted")
                cv_mean, cv_std = float(np.mean(cv_scores)), float(np.std(cv_scores))
            except Exception:
                cv_mean, cv_std = None, None
            results.append({"key": key, "name": label, "metrics": {
                "accuracy": _f(acc), "precision": _f(prec), "recall": _f(rec), "f1": _f(f1),
                "roc_auc": _f(roc), "cv_f1_mean": _f(cv_mean), "cv_f1_std": _f(cv_std)},
                "confusion_matrix": {"labels": [str(c)[:30] for c in sorted(y.unique().tolist())], "matrix": cm.tolist()},
                "n_train": len(X_train), "n_test": len(X_test)})

    ok = [r for r in results if "error" not in r]
    if not ok:
        raise ValueError("All models failed to train. " + "; ".join(r.get("error", "?") for r in results))
    # best model
    if task == "regression":
        best = max(ok, key=lambda r: (r["metrics"]["r2"] if r["metrics"]["r2"] is not None else -1e9))
        criterion = "R² (higher is better)"
        best_note = f"'{best['name']}' performed best according to R² ({best['metrics']['r2']}). A high score on a small or leaky sample does not mean the model is production-ready."
    else:
        best = max(ok, key=lambda r: (r["metrics"]["f1"] if r["metrics"]["f1"] is not None else -1e9))
        criterion = "weighted F1 (higher is better)"
        best_note = f"'{best['name']}' performed best according to weighted F1 ({best['metrics']['f1']}). Validate on fresh data before trusting it."

    # feature importance for tree models (best if tree)
    importance = None
    try:
        bkey = best["key"]
        pipe = fitted.get(bkey)
        model = pipe.named_steps["model"] if pipe is not None else None
        if pipe is not None and hasattr(model, "feature_importances_"):
            pre_fit = pipe.named_steps["pre"]
            try:
                names = pre_fit.get_feature_names_out().tolist()
            except Exception:
                names = [f"f{i}" for i in range(len(model.feature_importances_))]
            imp = sorted(zip(names, model.feature_importances_), key=lambda t: t[1], reverse=True)[:15]
            importance = [{"feature": str(n)[:60], "importance": round(float(v), 4)} for n, v in imp]
        elif pipe is not None and hasattr(model, "coef_"):
            try:
                names = pre_fit.get_feature_names_out().tolist()
            except Exception:
                names = [f"f{i}" for i in range(np.size(model.coef_))]
            coef = np.abs(np.ravel(model.coef_))
            imp = sorted(zip(names, coef), key=lambda t: t[1], reverse=True)[:15]
            importance = [{"feature": str(n)[:60], "importance": round(float(v), 4)} for n, v in imp]
    except Exception:
        importance = None

    code = _ml_code(target, task, wanted, feature_cols, test_size)
    payload = {
        "target": target, "task": task, "test_size": test_size,
        "features": feature_cols, "numeric_features": num_cols, "categorical_features": cat_cols,
        "dropped_target_na": dropped_target_na,
        "train_rows": len(X_raw),
        "cv_folds": eff_cv,
        "sampling_note": sampling_note,
        "results": results, "best": best["key"], "best_name": best["name"],
        "criterion": criterion, "best_note": best_note,
        "feature_importance": importance, "code": code,
        "warning": "Evaluate on held-out or future data. High in-sample scores can reflect leakage, duplicates, or a target that is derived from the features.",
    }
    # stash fitted best pipeline in-memory for prediction (keyed by id)
    run_id = f"run_{abs(hash((target, task, str(sorted(feature_cols))))) % 10**8}"
    _PIPELINES[run_id] = {"pipe": fitted[best["key"]], "features": feature_cols, "target": target,
                          "task": task, "classes": sorted(y.unique().tolist()) if task == "classification" else None,
                          "X_dtypes": {c: str(X_raw[c].dtype) for c in X_raw.columns}}
    payload["run_id"] = run_id
    return payload


_PIPELINES: dict[str, dict] = {}


def predict_with_run(run_id: str, values: dict) -> dict:
    if run_id not in _PIPELINES:
        raise ValueError("Model run expired (server restarted or new training run). Please retrain.")
    info = _PIPELINES[run_id]
    pipe = info["pipe"]
    features: list[str] = info["features"]
    row: dict = {}
    for f in features:
        v = values.get(f)
        # empty string -> NaN (imputer handles)
        if v == "" or v is None:
            row[f] = np.nan
        else:
            row[f] = v
    X = pd.DataFrame([row], columns=features)
    # coerce numeric-looking
    for c, dt in info["X_dtypes"].items():
        if c in X.columns and ("int" in dt or "float" in dt):
            X[c] = pd.to_numeric(X[c], errors="coerce")
        if "datetime" in dt:
            try:
                X[c] = pd.to_datetime(X[c], errors="coerce").map(lambda x: x.toordinal() if pd.notna(x) else np.nan)
            except Exception:
                X[c] = np.nan
    try:
        pred = pipe.predict(X)[0]
    except Exception as e:
        raise ValueError(f"Prediction failed: {e}")
    out: dict = {"prediction": (float(pred) if info["task"] == "regression" else str(pred)),
                 "task": info["task"], "target": info["target"]}
    if info["task"] == "classification":
        try:
            if hasattr(pipe, "predict_proba"):
                proba = pipe.predict_proba(X)[0]
                classes = pipe.classes_.tolist() if hasattr(pipe, "classes_") else info["classes"]
                out["probabilities"] = [{"class": str(c), "proba": round(float(p), 4)} for c, p in zip(classes, proba)]
        except Exception:
            pass
    return out


def _ml_code(target: str, task: str, models: list[str], features: list[str], test_size: float) -> str:
    if task == "regression":
        imports = "from sklearn.linear_model import LinearRegression\nfrom sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor\n"
        model_lines = {"linear": "LinearRegression()", "random_forest": "RandomForestRegressor(n_estimators=200, random_state=42)",
                       "gradient_boosting": "GradientBoostingRegressor(random_state=42)"}
    else:
        imports = "from sklearn.linear_model import LogisticRegression\nfrom sklearn.tree import DecisionTreeClassifier\nfrom sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier\nfrom sklearn.neighbors import KNeighborsClassifier\n"
        model_lines = {"logistic": "LogisticRegression(max_iter=2000)", "decision_tree": "DecisionTreeClassifier(random_state=42)",
                       "random_forest": "RandomForestClassifier(n_estimators=200, random_state=42)", "knn": "KNeighborsClassifier()",
                       "gradient_boosting": "GradientBoostingClassifier(random_state=42)"}
    chosen = ", ".join(f"{m!r}: {model_lines[m]}" for m in models if m in model_lines)
    return (
        "import pandas as pd\nfrom sklearn.model_selection import train_test_split\n"
        "from sklearn.compose import ColumnTransformer\nfrom sklearn.pipeline import Pipeline\n"
        "from sklearn.impute import SimpleImputer\nfrom sklearn.preprocessing import OneHotEncoder, StandardScaler\n"
        f"{imports}\n"
        f"# df is your DataFrame\nfeatures = {features!r}\ntarget = {target!r}\n"
        f"X = df[features].copy()\ny = df[target]\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size={test_size}, random_state=42)\n\n"
        "num_cols = X.select_dtypes(include='number').columns.tolist()\ncat_cols = [c for c in X.columns if c not in num_cols]\n"
        "pre = ColumnTransformer([\n    ('num', Pipeline([('imputer', SimpleImputer(strategy='median')), ('scaler', StandardScaler())]), num_cols),\n"
        "    ('cat', Pipeline([('imputer', SimpleImputer(strategy='most_frequent')), ('onehot', OneHotEncoder(handle_unknown='ignore'))]), cat_cols)])\n\n"
        f"models = {{{chosen}}}\nfor name, model in models.items():\n    pipe = Pipeline([('pre', pre), ('model', model)])\n    pipe.fit(X_train, y_train)\n    print(name, pipe.score(X_test, y_test))\n"
    )
