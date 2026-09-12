import React, { useEffect, useState } from 'react';
import { api, fmt } from '../lib/api';
import { Card, PageHeader, Spinner, ErrorBox, EmptyState, SeverityBadge, CodeViewer, Learn, Field } from '../components/ui';

type Issue = { id: string; severity: string; title: string; detail: string; columns: string[]; actions: string[] };

const ACTION_LABELS: Record<string, string> = {
  remove_duplicates: 'Remove duplicate rows',
  drop_column: 'Drop column',
  fill_mean: 'Fill with mean',
  fill_median: 'Fill with median',
  fill_mode: 'Fill with mode',
  ffill: 'Forward fill',
  bfill: 'Backward fill',
  drop_rows: 'Drop rows with missing',
  cap_outliers: 'Cap outliers (IQR)',
  drop_outliers: 'Drop outlier rows',
  trim_whitespace: 'Trim whitespace',
  standardize_case: 'Standardize case',
  convert_dtype: 'Convert datatype',
};

export default function Quality({ onChanged, refreshToken }: { onChanged: () => void; refreshToken: number }) {
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [cols, setCols] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [lastCode, setLastCode] = useState('');
  const [lastMsg, setLastMsg] = useState('');
  const [canUndo, setCanUndo] = useState(false);
  const [confirm, setConfirm] = useState<{ label: string; run: () => void } | null>(null);

  // manual cleaning form
  const [op, setOp] = useState('fill_missing');
  const [col, setCol] = useState('');
  const [strategy, setStrategy] = useState('median');
  const [newName, setNewName] = useState('');
  const [dtype, setDtype] = useState('numeric');
  const [caseOpt, setCaseOpt] = useState('lower');
  const [encMethod, setEncMethod] = useState('onehot');
  const [scaleMethod, setScaleMethod] = useState('standard');
  const [constVal, setConstVal] = useState('');

  const load = async () => {
  setLoading(true);
  setError('');

  try {
    const s = await api.summary() as {
      summary: Record<string, unknown>;
      quality?: Record<string, unknown>;
      columns?: string[];
      can_undo: boolean;
    };

    if (!s.quality) {
      throw new Error('Quality data unavailable');
    }

    setReport(s.quality);
    setSummary(s.summary);
    setCols(Array.isArray(s.columns) ? s.columns : []);
    setCanUndo(Boolean(s.can_undo));

    if (!col && Array.isArray(s.columns) && s.columns.length) {
      setCol(s.columns[0]);
    }
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : 'Failed';

    if (msg.includes('No dataset')) {
      setReport(null);
      setSummary(null);
    } else {
      setError(msg);
    }
  } finally {
    setLoading(false);
  }
};

  useEffect(() => { load(); }, [refreshToken]);

  const runOp = async (payload: Record<string, unknown>, label: string) => {
    setBusy(label); setLastMsg(''); setLastCode('');
    try {
      const res = await api.cleanApply(payload);
      setLastMsg(res.message); setLastCode(res.code || '');
      setCanUndo(res.can_undo);
      onChanged();
      await load();
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Operation failed'); }
    finally { setBusy(''); setConfirm(null); }
  };

  const askConfirm = (label: string, run: () => void) => {
    if (/drop|remove|reset/i.test(label)) setConfirm({ label, run });
    else run();
  };

  const issueAction = (issue: Issue, action: string) => {
    const c0 = issue.columns[0];
    const map: Record<string, Record<string, unknown>> = {
      remove_duplicates: { op: 'remove_duplicates' },
      drop_column: { op: 'drop_column', columns: issue.columns },
      fill_mean: { op: 'fill_missing', column: c0, strategy: 'mean' },
      fill_median: { op: 'fill_missing', column: c0, strategy: 'median' },
      fill_mode: { op: 'fill_missing', column: c0, strategy: 'mode' },
      ffill: { op: 'fill_missing', column: c0, strategy: 'ffill' },
      bfill: { op: 'fill_missing', column: c0, strategy: 'bfill' },
      drop_rows: { op: 'drop_rows_missing', columns: issue.columns },
      cap_outliers: { op: 'cap_outliers', column: c0 },
      drop_outliers: { op: 'drop_outliers', column: c0 },
      trim_whitespace: { op: 'trim_whitespace', columns: issue.columns },
      standardize_case: { op: 'standardize_case', column: c0, case: 'lower' },
      convert_dtype: { op: 'convert_dtype', column: c0, dtype: 'numeric' },
    };
    const payload = map[action];
    if (payload) askConfirm(`${ACTION_LABELS[action]} — ${c0 || 'dataset'}`, () => runOp(payload, action));
  };

  const runManual = () => {
    const builders: Record<string, () => Record<string, unknown>> = {
      fill_missing: () => ({ op: 'fill_missing', column: col, strategy, value: strategy === 'constant' ? constVal : undefined }),
      drop_rows_missing: () => ({ op: 'drop_rows_missing', columns: [col] }),
      drop_column: () => ({ op: 'drop_column', columns: [col] }),
      rename_column: () => ({ op: 'rename_column', old: col, new: newName }),
      convert_dtype: () => ({ op: 'convert_dtype', column: col, dtype }),
      trim_whitespace: () => ({ op: 'trim_whitespace', columns: [col] }),
      standardize_case: () => ({ op: 'standardize_case', column: col, case: caseOpt }),
      cap_outliers: () => ({ op: 'cap_outliers', column: col }),
      encode_categorical: () => ({ op: 'encode_categorical', column: col, method: encMethod }),
      scale_numeric: () => ({ op: 'scale_numeric', column: col, method: scaleMethod }),
      remove_duplicates: () => ({ op: 'remove_duplicates' }),
    };
    const b = builders[op];
    if (b) askConfirm(`${op} — ${col}`, () => runOp(b(), op));
  };

  if (loading) return <Spinner label="Scanning data quality…" />;
  if (error && !report) return <ErrorBox message={error} onRetry={load} />;
  if (!report) return <EmptyState title="No dataset loaded." body="Import a dataset to scan it for quality issues." />;

  const score = Number(report.score);
  const counts = report.counts as Record<string, number>;
  const issues = report.issues as Issue[];
  const s = summary as Record<string, unknown> | null;
  const color = score >= 85 ? '#66745A' : score >= 65 ? '#A68A64' : '#8C3B2E';

  return (
    <div className="page-enter">
      <PageHeader
        kicker="Data Quality"
        title="Quality Center"
        body="ORION scans for missingness, duplicates, outliers, and inconsistencies — then proposes safe, reversible fixes. Your original file is never modified."
        action={
          <div className="flex gap-2">
            <button
              onClick={async () => { try { await api.cleanUndo(); onChanged(); await load(); } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Undo failed'); } }}
              disabled={!canUndo} className="btn-ghost px-4 py-2 text-[13px] disabled:opacity-40"
            >
              ↩ Undo
            </button>
            <button onClick={() => askConfirm('Reset to original upload', async () => { await api.cleanReset(); onChanged(); await load(); })} className="btn-ghost px-4 py-2 text-[13px]">
              Reset
            </button>
          </div>
        }
      />

      {error && <div className="mb-3"><ErrorBox message={error} /></div>}
      {lastMsg && (
        <div className="card p-3.5 mb-3 !border-moss bg-[#EFF2EA] text-[13px]">
          <span className="font-semibold">✓ Applied: </span>{lastMsg}
          {lastCode && <CodeViewer code={lastCode} />}
        </div>
      )}

      <div className="grid md:grid-cols-4 gap-3">
        <Card title="Quality score" subtitle="Estimated from real checks">
          <div className="flex items-baseline gap-1.5">
            <span className="font-serif text-[40px] font-medium" style={{ color }}>{score}</span>
            <span className="text-muted text-[13px]">/ 100</span>
          </div>
          <div className="h-2.5 rounded-full bg-line mt-2 overflow-hidden">
            <div className="h-full rounded-full" style={{ width: `${score}%`, background: color }} />
          </div>
        </Card>
        {(['high', 'medium', 'low'] as const).map((k) => (
          <Card key={k} title={`${k[0].toUpperCase() + k.slice(1)} severity`} subtitle="issues found">
            <div className="font-serif text-[40px] font-medium">{counts[k]}</div>
          </Card>
        ))}
      </div>

      {s && (
        <div className="text-[12.5px] text-muted mt-2">
          {fmt(s.rows)} rows · {fmt(s.missing_cells)} missing cells ({String(s.missing_pct)}%) · {fmt(s.duplicate_rows)} duplicates · {(s.ops as unknown[])?.length || 0} cleaning ops this session
        </div>
      )}

      <div className="grid lg:grid-cols-2 gap-3 mt-3">
        <div>
          <h2 className="text-[14px] font-semibold mb-2">Detected issues ({issues.length}{Number(report.total_issues) > issues.length ? ` of ${report.total_issues}` : ''})</h2>
          <div className="space-y-2.5 max-h-[640px] overflow-y-auto pr-1">
            {issues.length === 0 && <Card><div className="text-[13.5px]">✓ No issues detected. This dataset looks clean.</div></Card>}
            {issues.map((iss) => (
              <Card key={iss.id} className="!p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="text-[13.5px] font-semibold leading-snug">{iss.title}</div>
                  <SeverityBadge level={iss.severity} />
                </div>
                <p className="text-[12.5px] text-muted mt-1.5 leading-relaxed">{iss.detail}</p>
                <div className="flex flex-wrap gap-1.5 mt-2.5">
                  {iss.actions.map((a) => (
                    <button
                      key={a} disabled={!!busy} onClick={() => issueAction(iss, a)}
                      className="btn-ghost px-2.5 py-1 text-[12px] bg-white disabled:opacity-40"
                    >
                      {busy === a ? '…' : ACTION_LABELS[a] || a}
                    </button>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        </div>

        <div>
          <h2 className="text-[14px] font-semibold mb-2">Cleaning workbench</h2>
          <Card title="Apply a transformation" subtitle="Preview destructive ops via confirmation · everything is undoable">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Operation">
                <select value={op} onChange={(e) => setOp(e.target.value)} className="select w-full px-2.5 py-2 text-[13px]">
                  <option value="fill_missing">Fill missing values</option>
                  <option value="drop_rows_missing">Drop rows with missing</option>
                  <option value="remove_duplicates">Remove duplicates</option>
                  <option value="drop_column">Drop column</option>
                  <option value="rename_column">Rename column</option>
                  <option value="convert_dtype">Convert datatype</option>
                  <option value="trim_whitespace">Trim whitespace</option>
                  <option value="standardize_case">Standardize case</option>
                  <option value="cap_outliers">Cap outliers</option>
                  <option value="encode_categorical">Encode categorical</option>
                  <option value="scale_numeric">Scale / transform numeric</option>
                </select>
              </Field>
              {op !== 'remove_duplicates' && (
                <Field label="Column">
                  <select value={col} onChange={(e) => setCol(e.target.value)} className="select w-full px-2.5 py-2 text-[13px]">
                    {cols.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </Field>
              )}
              {op === 'fill_missing' && (
                <Field label="Strategy">
                  <select value={strategy} onChange={(e) => setStrategy(e.target.value)} className="select w-full px-2.5 py-2 text-[13px]">
                    <option value="median">Median (robust)</option>
                    <option value="mean">Mean</option>
                    <option value="mode">Mode (most common)</option>
                    <option value="ffill">Forward fill</option>
                    <option value="bfill">Backward fill</option>
                    <option value="zero">Zero</option>
                    <option value="constant">Constant value…</option>
                  </select>
                </Field>
              )}
              {op === 'fill_missing' && strategy === 'constant' && (
                <Field label="Value"><input value={constVal} onChange={(e) => setConstVal(e.target.value)} className="input w-full px-2.5 py-2 text-[13px]" placeholder="e.g. Unknown" /></Field>
              )}
              {op === 'rename_column' && (
                <Field label="New name"><input value={newName} onChange={(e) => setNewName(e.target.value)} className="input w-full px-2.5 py-2 text-[13px]" placeholder="new_column_name" /></Field>
              )}
              {op === 'convert_dtype' && (
                <Field label="Target type">
                  <select value={dtype} onChange={(e) => setDtype(e.target.value)} className="select w-full px-2.5 py-2 text-[13px]">
                    <option value="numeric">Numeric</option>
                    <option value="datetime">Datetime</option>
                    <option value="string">String</option>
                    <option value="category">Category</option>
                    <option value="int">Integer</option>
                    <option value="float">Float</option>
                  </select>
                </Field>
              )}
              {op === 'standardize_case' && (
                <Field label="Case">
                  <select value={caseOpt} onChange={(e) => setCaseOpt(e.target.value)} className="select w-full px-2.5 py-2 text-[13px]">
                    <option value="lower">lower</option>
                    <option value="upper">UPPER</option>
                    <option value="title">Title</option>
                  </select>
                </Field>
              )}
              {op === 'encode_categorical' && (
                <Field label="Method">
                  <select value={encMethod} onChange={(e) => setEncMethod(e.target.value)} className="select w-full px-2.5 py-2 text-[13px]">
                    <option value="onehot">One-hot</option>
                    <option value="label">Label encoding</option>
                  </select>
                </Field>
              )}
              {op === 'scale_numeric' && (
                <Field label="Method">
                  <select value={scaleMethod} onChange={(e) => setScaleMethod(e.target.value)} className="select w-full px-2.5 py-2 text-[13px]">
                    <option value="standard">Standardize (z-score)</option>
                    <option value="minmax">Min-max [0,1]</option>
                    <option value="log">Log1p</option>
                  </select>
                </Field>
              )}
            </div>
            <button onClick={runManual} disabled={!!busy} className="btn-moss px-4 py-2 text-[13.5px] mt-3 disabled:opacity-50">
              {busy ? 'Applying…' : 'Apply transformation'}
            </button>
            <Learn title="safe cleaning">
              Cleaning changes analysis, so ORION never touches your original file, confirms destructive actions,
              and keeps an undo stack. Prefer reversible, explainable steps: trim whitespace before encoding,
              and understand <em>why</em> values are missing before imputing them.
            </Learn>
          </Card>

          <Card title="Session history" subtitle="Operations applied since import" className="mt-3">
  {s && Array.isArray(s.ops) && s.ops.length === 0 && (
    <div className="text-[13px] text-muted">No operations yet.</div>
  )}

  {s && !Array.isArray(s.ops) && (
    <div className="text-[13px] text-muted">No operations yet.</div>
  )}

  <ul className="space-y-1.5 text-[12.5px] max-h-[220px] overflow-y-auto">
    {s && Array.isArray(s.ops) &&
      (s.ops as { label: string; at: string }[]).map((o, i) => (
        <li key={i} className="flex gap-2 border-b border-line/60 pb-1.5">
          <span className="text-bronze font-semibold">{i + 1}.</span>
          <span>{o.label}</span>
        </li>
      ))}
  </ul>
</Card>
        </div>
      </div>

      {confirm && (
        <div className="fixed inset-0 bg-ink/40 flex items-center justify-center z-50 p-4" role="dialog" aria-modal="true" aria-label="Confirm action">
          <div className="card p-6 max-w-md w-full">
            <h3 className="font-serif text-[20px] font-medium">Confirm this change?</h3>
            <p className="text-[13.5px] text-muted mt-2">“{confirm.label}” will modify your working copy. Your original file stays untouched, and you can undo afterwards.</p>
            <div className="flex gap-2 mt-4 justify-end">
              <button onClick={() => setConfirm(null)} className="btn-ghost px-4 py-2 text-[13px]">Cancel</button>
              <button onClick={confirm.run} className="btn-primary px-4 py-2 text-[13px]">Apply</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
