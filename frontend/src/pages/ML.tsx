import React, { useEffect, useState } from 'react';
import { api, fmt } from '../lib/api';
import { Card, PageHeader, Spinner, EmptyState, ErrorBox, CodeViewer, Learn, Field } from '../components/ui';

type Suggestion = { column: string; task: string; suitable: boolean; reason: string; unique: number; missing_pct: number; classes?: string[] };

const REGISTRY: Record<string, string[]> = {
  regression: ['linear', 'random_forest', 'gradient_boosting'],
  classification: ['logistic', 'decision_tree', 'random_forest', 'knn', 'gradient_boosting'],
};
const MODEL_LABEL: Record<string, string> = {
  linear: 'Linear Regression', random_forest: 'Random Forest', gradient_boosting: 'Gradient Boosting',
  logistic: 'Logistic Regression', decision_tree: 'Decision Tree', knn: 'K-Nearest Neighbors',
};

export default function ML({ refreshToken }: { refreshToken: number }) {
  const [sugg, setSugg] = useState<Suggestion[] | null>(null);
  const [cols, setCols] = useState<string[]>([]);
  const [target, setTarget] = useState('');
  const [task, setTask] = useState<'regression' | 'classification'>('regression');
  const [models, setModels] = useState<string[]>(['linear', 'random_forest']);
  const [testSize, setTestSize] = useState(0.2);
  const [exclude, setExclude] = useState<string[]>([]);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [predVals, setPredVals] = useState<Record<string, string>>({});
  const [predOut, setPredOut] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([api.mlTargets(), api.columns()])
      .then(([t, c]) => {
        setSugg(t.suggestions);
        setCols(c.columns);
        const first = (t.suggestions as Suggestion[]).find((s) => s.suitable);
        if (first) {
          setTarget(first.column);
          const tk = first.task === 'classification' ? 'classification' : 'regression';
          setTask(tk);
          setModels(tk === 'regression' ? ['linear', 'random_forest'] : ['logistic', 'random_forest']);
        }
      })
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : 'Failed';
        if (!msg.includes('No dataset')) setError(msg);
      })
      .finally(() => setLoading(false));
  }, [refreshToken]);

  const train = async () => {
    if (!target) { setError('Choose a target column first.'); return; }
    setBusy(true); setError(''); setResult(null); setPredOut(null);
    try {
      const res = await api.mlTrain({ target, task, models, test_size: testSize, exclude });
      setResult(res);
      const feats = res.features as string[];
      const init: Record<string, string> = {};
      feats.forEach((f) => { init[f] = ''; });
      setPredVals(init);
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Training failed'); }
    finally { setBusy(false); }
  };

  const predict = async () => {
    if (!result) return;
    setBusy(true); setError('');
    try {
      const vals: Record<string, unknown> = {};
      Object.entries(predVals).forEach(([k, v]) => {
        const trimmed = v.trim();
        if (trimmed === '') vals[k] = null;
        else if (!isNaN(Number(trimmed)) && trimmed !== '') vals[k] = Number(trimmed);
        else vals[k] = trimmed;
      });
      setPredOut(await api.mlPredict(String(result.run_id), vals));
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Prediction failed'); }
    finally { setBusy(false); }
  };

  if (loading) return <Spinner label="Assessing ML suitability…" />;
  if (!sugg) return <EmptyState title="No dataset loaded." body="Import a dataset, then choose a target to train models." />;

  return (
    <div className="page-enter">
      <PageHeader kicker="Machine Learning" title="ML Lab" body="ORION suggests targets but never picks one silently. Compare models honestly — a high score alone never means production-ready." />
      {error && <div className="mb-3"><ErrorBox message={error} /></div>}

      <div className="grid lg:grid-cols-3 gap-3">
        <Card title="1 · Choose a target" subtitle="You decide what to predict">
          <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
            {sugg.map((s) => (
              <button
                key={s.column}
                onClick={() => { setTarget(s.column); if (s.task === 'classification' || s.task === 'regression') { setTask(s.task); setModels(s.task === 'regression' ? ['linear', 'random_forest'] : ['logistic', 'random_forest']); } }}
                className={`w-full text-left p-3 rounded-[8px] border ${target === s.column ? 'border-ink bg-ink text-surface' : 'border-line bg-white hover:border-bronze'}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[13.5px] font-semibold truncate">{s.column}</span>
                  <span className={`text-[10.5px] font-semibold px-2 py-0.5 rounded-full ${s.suitable ? 'bg-moss text-surface' : target === s.column ? 'bg-panelsoft text-line' : 'bg-sand text-muted'}`}>
                    {s.task} {s.suitable ? '· suitable' : '· check'}
                  </span>
                </div>
                <div className={`text-[12px] mt-1 leading-relaxed ${target === s.column ? 'text-line/85' : 'text-muted'}`}>{s.reason}</div>
              </button>
            ))}
          </div>
        </Card>

        <Card title="2 · Configure training" subtitle="Preprocessing is automatic & explicit">
          <div className="space-y-3">
            <Field label="Task">
              <div className="grid grid-cols-2 gap-1.5">
                {(['regression', 'classification'] as const).map((t) => (
                  <button key={t} onClick={() => { setTask(t); setModels(t === 'regression' ? ['linear', 'random_forest'] : ['logistic', 'random_forest']); }} className={`px-3 py-2 text-[13px] rounded-[8px] border font-medium ${task === t ? 'bg-ink text-surface border-ink' : 'bg-white border-line'}`}>{t}</button>
                ))}
              </div>
            </Field>
            <Field label="Models to compare">
              <div className="space-y-1.5">
                {REGISTRY[task].map((m) => (
                  <label key={m} className="flex items-center gap-2 text-[13px] bg-white border border-line rounded-[8px] px-3 py-1.5 cursor-pointer">
                    <input type="checkbox" checked={models.includes(m)} onChange={(e) => setModels(e.target.checked ? [...models, m] : models.filter((x) => x !== m))} className="accent-[#66745A]" />
                    {MODEL_LABEL[m]}
                  </label>
                ))}
              </div>
            </Field>
            <Field label={`Test size (${Math.round(testSize * 100)}%)`}>
              <input type="range" min={10} max={40} value={Math.round(testSize * 100)} onChange={(e) => setTestSize(Number(e.target.value) / 100)} className="w-full" />
            </Field>
            <Field label="Exclude columns (IDs, leakage)" hint="Hold Ctrl/Cmd to multi-select">
              <select multiple value={exclude} onChange={(e) => setExclude([...e.target.selectedOptions].map((o) => o.value))} className="select w-full px-2 py-2 text-[13px] h-[84px]">
                {cols.filter((c) => c !== target).map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </Field>
            <button onClick={train} disabled={busy || !target || models.length === 0} className="btn-moss w-full py-2.5 text-[14px] disabled:opacity-50">
              {busy ? 'Training…' : `Train ${models.length} model${models.length === 1 ? '' : 's'}`}
            </button>
            <p className="text-[11.5px] text-muted leading-relaxed">
              Pipeline per model: median/mode imputation → standard scaling (numeric) → one-hot encoding (categorical) →
              stratified split · 5-fold cross-validation. Random state fixed for reproducibility.
            </p>
          </div>
        </Card>

        <Card title="3 · Results & prediction" subtitle="Training result ≠ new prediction">
          {!result && <div className="text-[13px] text-muted py-8 text-center">Train models to see comparison, metrics, and the prediction workspace.</div>}
          {result && <ResultsView result={result} />}
        </Card>
      </div>

      {result && (
        <div className="grid lg:grid-cols-2 gap-3 mt-3">
          <Card title="New prediction" subtitle={`Using ${String(result.best_name)} → target “${String(result.target)}”`}>
            <div className="grid grid-cols-2 gap-2.5 max-h-[300px] overflow-y-auto pr-1">
              {(result.features as string[]).map((f) => (
                <Field key={f} label={f}>
                  <input value={predVals[f] || ''} onChange={(e) => setPredVals({ ...predVals, [f]: e.target.value })} placeholder="value…" className="input w-full px-2.5 py-1.5 text-[13px]" />
                </Field>
              ))}
            </div>
            <button onClick={predict} disabled={busy} className="btn-primary px-4 py-2 text-[13px] mt-3 disabled:opacity-50">Predict</button>
            {predOut && (
              <div className="card !bg-panel !border-panel text-[#F3EFE6] p-4 mt-3">
                <div className="text-[11px] uppercase tracking-[0.1em] text-[#B9B7AC] font-semibold">New prediction (not a training result)</div>
                <div className="font-serif text-[28px] font-medium mt-1">{String(predOut.prediction)}</div>
                {Array.isArray(predOut.probabilities) && (
                  <div className="mt-2 space-y-1">
                    {(predOut.probabilities as { class: string; proba: number }[]).map((p) => (
                      <div key={p.class} className="flex items-center gap-2 text-[12.5px]">
                        <span className="w-[120px] truncate">{p.class}</span>
                        <div className="flex-1 h-1.5 bg-panelsoft rounded-full overflow-hidden">
                          <div className="h-full bg-bronze rounded-full" style={{ width: `${p.proba * 100}%` }} />
                        </div>
                        <span>{(p.proba * 100).toFixed(1)}%</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </Card>
          <div>
            <CodeViewer code={String(result.code || '')} title="View Python Code (sklearn pipeline)" />
            <Learn title="reading ML results">
              Compare models on the <b>same criterion</b> ({String(result.criterion)}). Cross-validation scores estimate
              performance on new data better than a single split. If scores look “too good”, suspect <b>leakage</b> —
              a feature that already contains the answer (e.g. predicting revenue from a column derived from revenue).
            </Learn>
            <div className="explain-box rounded-[8px] px-3.5 py-2.5 mt-3 text-[12.5px]">⚠ {String(result.warning)}</div>
          </div>
        </div>
      )}
    </div>
  );
}

function ResultsView({ result }: { result: Record<string, unknown> }) {
  const results = result.results as { key: string; name: string; error?: string; metrics?: Record<string, number | null>; confusion_matrix?: { labels: string[]; matrix: number[][] } }[];
  return (
    <div>
      <div className="card !bg-[#EFF2EA] !border-moss p-3 text-[12.5px] mb-2.5">
        <b>🏆 {String(result.best_name)}</b> — {String(result.best_note)}
      </div>
      {typeof result.sampling_note === 'string' && result.sampling_note && (
        <div className="explain-box rounded-[8px] px-3 py-2 text-[12px] mb-2.5">ⓘ {result.sampling_note} · CV folds: {String(result.cv_folds)}</div>
      )}
      <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
        {results.map((r) => (
          <div key={r.key} className={`border rounded-[8px] p-3 ${r.key === result.best ? 'border-moss bg-white' : 'border-line bg-white'}`}>
            <div className="flex items-center justify-between">
              <span className="text-[13.5px] font-semibold">{r.name}</span>
              {r.key === result.best && <span className="text-[10.5px] font-semibold px-2 py-0.5 rounded-full bg-moss text-surface">best</span>}
            </div>
            {r.error && <div className="text-[12.5px] text-[#8C3B2E] mt-1">{r.error}</div>}
            {r.metrics && (
              <div className="grid grid-cols-3 gap-1.5 mt-2">
                {Object.entries(r.metrics).filter(([, v]) => v !== null).map(([k, v]) => (
                  <div key={k} className="bg-sand rounded-[7px] px-2 py-1.5">
                    <div className="text-[9.5px] uppercase tracking-wider text-muted font-semibold">{k}</div>
                    <div className="text-[13px] font-semibold">{fmt(v)}</div>
                  </div>
                ))}
              </div>
            )}
            {r.confusion_matrix && <ConfMatrix cm={r.confusion_matrix} />}
          </div>
        ))}
      </div>
      {Array.isArray(result.feature_importance) && (result.feature_importance as unknown[]).length > 0 && (
        <div className="mt-3">
          <div className="text-[12.5px] font-semibold mb-1.5">Top features ({String(result.best_name)})</div>
          {(result.feature_importance as { feature: string; importance: number }[]).slice(0, 8).map((f) => (
            <div key={f.feature} className="flex items-center gap-2 text-[12px]">
              <span className="w-[170px] truncate font-mono" title={f.feature}>{f.feature}</span>
              <div className="flex-1 h-1.5 bg-sand rounded-full overflow-hidden">
                <div className="h-full bg-bronze rounded-full" style={{ width: `${Math.min(100, f.importance * 400)}%` }} />
              </div>
              <span className="text-muted">{f.importance.toFixed(3)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ConfMatrix({ cm }: { cm: { labels: string[]; matrix: number[][] } }) {
  const max = Math.max(1, ...cm.matrix.flat());
  return (
    <div className="mt-2">
      <div className="text-[11px] font-semibold text-muted mb-1">Confusion matrix (rows = actual, cols = predicted)</div>
      <div className="table-wrap overflow-auto border border-line rounded-[7px]">
        <table>
          <thead><tr><th></th>{cm.labels.map((l) => <th key={l}>{l}</th>)}</tr></thead>
          <tbody>
            {cm.labels.map((l, i) => (
              <tr key={l}>
                <td className="!font-semibold">{l}</td>
                {cm.matrix[i].map((v, j) => (
                  <td key={j} style={{ background: `rgba(102,116,90,${(v / max) * 0.4})` }} className={i === j ? '!font-bold' : ''}>{v}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
