import React, { useEffect, useState } from 'react';
import { api, fmt } from '../lib/api';
import { Card, PageHeader, Spinner, ErrorBox, EmptyState, CodeViewer, Learn, Field } from '../components/ui';
import { PlotView, UnivPlots } from '../components/PlotView';

export default function Explore({ refreshToken }: { refreshToken: number }) {
  const [cols, setCols] = useState<{ columns: string[]; numeric: string[]; categorical: string[]; datetime: string[] } | null>(null);
  const [col, setCol] = useState('');
  const [univ, setUniv] = useState<Record<string, unknown> | null>(null);
  const [bx, setBx] = useState(''); const [by, setBy] = useState('');
  const [biv, setBiv] = useState<Record<string, unknown> | null>(null);
  const [corr, setCorr] = useState<Record<string, unknown> | null>(null);
  const [corrMethod, setCorrMethod] = useState('pearson');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');

  useEffect(() => {
    setLoading(true); setError('');
    api.columns()
      .then((c) => {
        setCols(c);
        if (c.columns.length) {
          const first = c.numeric[0] || c.columns[0];
          setCol(first);
          setBx(c.numeric[0] || c.columns[0]);
          setBy(c.numeric[1] || c.categorical[0] || c.columns[1] || c.columns[0]);
          return first;
        }
        return '';
      })
      .then((first) => { if (first) return api.univariate(first).then(setUniv).catch(() => {}); })
      .then(() => api.corrMatrix('pearson').then(setCorr).catch(() => setCorr(null)))
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : 'Failed';
        if (msg.includes('No dataset')) setCols(null); else setError(msg);
      })
      .finally(() => setLoading(false));
  }, [refreshToken]);

  const runUniv = async (c: string) => {
    setBusy('univ');
    try { setUniv(await api.univariate(c)); } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Failed'); }
    finally { setBusy(''); }
  };

  const runBiv = async () => {
    if (!bx || !by) return;
    setBusy('biv');
    try { setBiv(await api.bivariate(bx, by)); } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Failed'); }
    finally { setBusy(''); }
  };

  const runCorr = async (m: string) => {
    setCorrMethod(m); setBusy('corr');
    try { setCorr(await api.corrMatrix(m)); } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Failed'); }
    finally { setBusy(''); }
  };

  useEffect(() => { if (bx && by && cols) runBiv(); }, [cols]);

  if (loading) return <Spinner label="Preparing EDA workspace…" />;
  if (!cols) return <EmptyState title="No dataset loaded." body="Import a dataset to explore distributions, relationships, and correlations." />;
  if (error && !univ && !corr) return <ErrorBox message={error} />;

  return (
    <div className="page-enter">
      <PageHeader kicker="Explore" title="Exploratory Analysis" body="Understand one variable at a time, then how variables relate. Charts are computed from your real data." />

      <div className="grid lg:grid-cols-2 gap-3">
        <Card
          title="Univariate analysis" subtitle="Distribution of a single column"
          action={
            <select value={col} onChange={(e) => { setCol(e.target.value); runUniv(e.target.value); }} className="select px-2.5 py-1.5 text-[13px] max-w-[200px]" aria-label="Column">
              {cols.columns.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          }
        >
          {busy === 'univ' && <Spinner />}
          {univ && <UnivDetail data={univ} />}
        </Card>

        <Card
          title="Bivariate analysis" subtitle="How two columns relate — chart auto-recommended"
          action={<button onClick={runBiv} disabled={busy === 'biv'} className="btn-ghost px-3 py-1.5 text-[12.5px]">{busy === 'biv' ? '…' : 'Analyze'}</button>}
        >
          <div className="grid grid-cols-2 gap-2.5 mb-3">
            <Field label="X"><select value={bx} onChange={(e) => setBx(e.target.value)} className="select w-full px-2 py-1.5 text-[13px]">{cols.columns.map((c) => <option key={c} value={c}>{c}</option>)}</select></Field>
            <Field label="Y"><select value={by} onChange={(e) => setBy(e.target.value)} className="select w-full px-2 py-1.5 text-[13px]">{cols.columns.map((c) => <option key={c} value={c}>{c}</option>)}</select></Field>
          </div>
          {biv && <BivDetail data={biv} />}
        </Card>
      </div>

      <Card
        title="Correlation matrix" subtitle="Linear associations between numeric columns"
        className="mt-3"
        action={
          <div className="flex gap-1.5">
            {['pearson', 'spearman', 'kendall'].map((m) => (
              <button key={m} onClick={() => runCorr(m)} className={`px-3 py-1.5 text-[12.5px] rounded-[8px] border ${corrMethod === m ? 'bg-ink text-surface border-ink' : 'btn-ghost'}`}>{m}</button>
            ))}
          </div>
        }
      >
        {busy === 'corr' && <Spinner />}
        {corr ? (
          <div className="grid lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2"><PlotView chart={{ ...(corr as object), type: 'heatmap' }} height={Math.min(560, Math.max(380, ((corr.columns as string[]) || []).length * 34 + 140))} /></div>
            <div>
              <div className="text-[12.5px] font-semibold mb-2">Strongest pairs</div>
              <ul className="space-y-1.5 text-[12.5px]">
                {((corr.pairs as { x: string; y: string; r: number }[]) || []).slice(0, 8).map((p, i) => (
                  <li key={i} className="flex justify-between gap-2 border-b border-line/60 pb-1.5">
                    <span className="truncate">{p.x} ↔ {p.y}</span>
                    <span className={`font-semibold ${Math.abs(p.r) >= 0.6 ? 'text-mossdark' : ''}`}>{p.r.toFixed(3)}</span>
                  </li>
                ))}
              </ul>
              <Learn title="correlation">Pearson captures <em>linear</em> relationships; Spearman captures any monotonic trend and resists outliers. A high value means the columns move together — not that one causes the other.</Learn>
              <CodeViewer code={String(corr.code || '')} />
            </div>
          </div>
        ) : (
          <div className="text-[13px] text-muted">Need at least 2 numeric columns for a correlation matrix.</div>
        )}
      </Card>
    </div>
  );
}

function UnivDetail({ data }: { data: Record<string, unknown> }) {
  const stats = data.stats as Record<string, unknown>;
  const entries = Object.entries(stats).filter(([, v]) => v !== null && v !== undefined);
  return (
    <div>
      <UnivPlots data={data as unknown as { plots: Record<string, unknown>; column: string }} />
      <div className="grid grid-cols-3 md:grid-cols-4 gap-1.5 mt-3">
        {entries.map(([k, v]) => (
          <div key={k} className="bg-white border border-line rounded-[8px] px-2.5 py-1.5">
            <div className="text-[10px] uppercase tracking-[0.06em] text-muted font-semibold">{k}</div>
            <div className="text-[13px] font-semibold truncate" title={String(v)}>{typeof v === 'number' ? fmt(v) : String(v)}</div>
          </div>
        ))}
      </div>
      <Learn title="reading distributions">
        For numbers, compare <b>mean vs median</b>: a large gap signals skew or outliers. For categories, check whether one
        value dominates — imbalance affects both charts and models.
      </Learn>
      <CodeViewer code={String(data.code || '')} />
    </div>
  );
}

function BivDetail({ data }: { data: Record<string, unknown> }) {
  return (
    <div>
      <div className="text-[12.5px] text-muted mb-2">
        Recommended view: <b className="text-ink">{String(data.recommendation)}</b>
        {typeof data.correlation === 'number' && <> · Pearson r = <b className="text-ink">{(data.correlation as number).toFixed(3)}</b></>}
      </div>
      {Boolean(data.chart) && <PlotView chart={data.chart as Record<string, unknown>} height={300} />}
      {Array.isArray(data.group_means) && (
        <div className="mt-2 text-[12.5px]">
          <div className="font-semibold mb-1">Group means</div>
          {(data.group_means as { group: string; mean: number }[]).slice(0, 8).map((g, i) => (
            <div key={i} className="flex justify-between border-b border-line/60 py-1">
              <span className="truncate">{g.group}</span><span className="font-semibold">{fmt(g.mean)}</span>
            </div>
          ))}
        </div>
      )}
      {Boolean(data.crosstab) && <Crosstab ct={data.crosstab as { rows: string[]; cols: string[]; values: number[][] }} />}
      <CodeViewer code={String((data.chart as Record<string, unknown> | undefined)?.code || data.code || '')} />
    </div>
  );
}

function Crosstab({ ct }: { ct: { rows: string[]; cols: string[]; values: number[][] } }) {
  const max = Math.max(1, ...ct.values.flat());
  return (
    <div className="table-wrap overflow-auto max-h-[280px] border border-line rounded-[8px] mt-2">
      <table>
        <thead><tr><th></th>{ct.cols.map((c) => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>
          {ct.rows.map((r, i) => (
            <tr key={r}>
              <td className="!font-semibold">{r}</td>
              {ct.values[i].map((v, j) => (
                <td key={j} style={{ background: `rgba(102,116,90,${(v / max) * 0.35})` }}>{v}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
