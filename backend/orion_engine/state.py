"""In-memory session state. No database. Single-user local workstation."""
from __future__ import annotations
import copy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
import pandas as pd


@dataclass
class DatasetState:
    df: pd.DataFrame
    original_df: pd.DataFrame
    filename: str
    filetype: str
    uploaded_at: datetime
    history: list[dict] = field(default_factory=list)      # undo stack of {label, df snapshot info, op}
    redo_stack: list[dict] = field(default_factory=list)
    ops_log: list[dict] = field(default_factory=list)      # human-readable cleaning log
    analysis_log: list[dict] = field(default_factory=list) # recent analysis events
    ml_runs: list[dict] = field(default_factory=list)
    code_log: list[dict] = field(default_factory=list)


class SessionStore:
    """Holds the current dataset in process memory only."""

    def __init__(self, max_history: int = 30):
        self.current: Optional[DatasetState] = None
        self.max_history = max_history

    def has_data(self) -> bool:
        return self.current is not None and self.current.df is not None

    def set_dataset(self, df: pd.DataFrame, filename: str, filetype: str):
        self.current = DatasetState(
            df=df.copy(deep=True),
            original_df=df.copy(deep=True),
            filename=filename,
            filetype=filetype,
            uploaded_at=datetime.now(),
        )
        self.log_analysis("import", f"Imported {filename} ({df.shape[0]:,} rows × {df.shape[1]} columns)")

    def get_df(self) -> pd.DataFrame:
        if not self.has_data():
            raise ValueError("No dataset loaded")
        assert self.current is not None
        return self.current.df

    def push_history(self, label: str, op: dict):
        """Snapshot current df BEFORE applying op, so undo can restore."""
        if not self.has_data():
            return
        assert self.current is not None
        snap = self.current.df.copy(deep=True)
        self.current.history.append({"label": label, "snapshot": snap, "op": op, "at": datetime.now().isoformat()})
        if len(self.current.history) > self.max_history:
            self.current.history.pop(0)
        self.current.redo_stack.clear()

    def apply_df(self, new_df: pd.DataFrame, label: str, op: dict, code: str = ""):
        assert self.current is not None
        self.push_history(label, op)
        self.current.df = new_df
        entry = {"label": label, "op": op, "at": datetime.now().isoformat()}
        self.current.ops_log.append(entry)
        self.log_analysis("clean", label)
        if code:
            self.current.code_log.append({"label": label, "code": code, "at": datetime.now().isoformat()})

    def undo(self) -> Optional[str]:
        if not self.has_data():
            return None
        assert self.current is not None
        if not self.current.history:
            return None
        last = self.current.history.pop()
        # save current for redo
        self.current.redo_stack.append({"label": last["label"], "snapshot": self.current.df.copy(deep=True)})
        self.current.df = last["snapshot"]
        if self.current.ops_log:
            self.current.ops_log.pop()
        self.log_analysis("clean", f"Undid: {last['label']}")
        return last["label"]

    def log_analysis(self, kind: str, label: str):
        if self.current is None:
            return
        self.current.analysis_log.append({"kind": kind, "label": label, "at": datetime.now().isoformat()})
        # keep last 50
        self.current.analysis_log = self.current.analysis_log[-50:]

    def reset_to_original(self):
        if not self.has_data():
            return
        assert self.current is not None
        self.push_history("Reset to original", {"op": "reset"})
        self.current.df = self.current.original_df.copy(deep=True)
        self.current.ops_log.append({"label": "Reset to original upload", "op": {"op": "reset"}, "at": datetime.now().isoformat()})


store = SessionStore()
