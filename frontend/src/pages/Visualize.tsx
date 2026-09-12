import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { Card, PageHeader, Spinner, EmptyState, ErrorBox, CodeViewer, Field } from '../components/ui';
import { PlotView } from '../components/PlotView';

const TYPES = [
  ['bar', 'Bar'], ['line', 'Line'], ['area', 'Area'], ['histogram', 'Histogram'],
  ['box', 'Box plot'], ['scatter', 'Scatter'], ['pie', 'Pie'], ['donut', 'Donut'], ['heatmap', 'Heatmap (corr)'],
];

export default function Visualize({ refreshToken }: { refreshToken: number }) {
  const [cols, setCols] = useState<{ columns: string[]; numeric: string[]; categorical: string[]; datetime: string[] } | null>(null);
  const [type, setType] = useState('bar');
  const [x, setX] = useState(''); const [y, setY] = useState('');
  const [group, setGroup] = useState(''); const [agg, setAgg] = useState('mean');
  const [bins, setBins] = useState(30); const [topN, setTopN] = useState(15);
  const [chart, setChart] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.columns()
      .then((c) => {
        setCols(c);
        setX(c.categorical[0] || c.columns[0]);
        setY(c.numeric[0] || '');
      })
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : 'Failed';
        if (!msg.includes('No dataset')) setError(msg);
      })
      .finally(() => setLoading(false));
  }, [refreshToken]);

  const build = async () => {
    setBusy(true); setError('');
    try {
      const res = await api.chart({ type, x: x || undefined, y: y || undefined, group: group || undefined, agg, bins, top_n: topN });
      setChart(res.chart);
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Chart failed'); }
    finally { setBusy(false); }
  };

  useEffect(() => { if (cols && x) build(); }, [cols]);

  if (loading) return <Spinner label="Loading chart builder…" />;
  if (!cols) return <EmptyState title="No dataset loaded." body="Import a dataset to build charts from real values." />;

  return (
    <div className="page-enter">
      <PageHeader kicker="Visualize" title="Chart Builder" body="Every chart is computed live from your dataset. Export any chart as PNG from the toolbar." />
      {error && <div className="mb-3"><ErrorBox message={error} /></div>}

      <div className="grid lg:grid-cols-4 gap-3">
        <Card title="Configuration" subtitle="Pick a mark and map columns">
          <div className="space-y-3">
            <Field label="Chart type">
              <div className="grid grid-cols-3 gap-1.5">
                {TYPES.map(([v, l]) => (
                  <button key={v} onClick={() => setType(v)} className={`px-2 py-1.5 text-[12px] rounded-[7px] border font-medium ${type === v ? 'bg-ink text-surface border-ink' : 'bg-white border-line hover:border-bronze'}`}>{l}</button>
                ))}
              </div>
            </Field>
            {type !== 'heatmap' && (
              <Field label={type === 'histogram' ? 'Column' : type === 'box' ? 'X (categories, optional → use Group)' : 'X axis'}>
                <select value={type === 'box' ? group : x} onChange={(e) => type === 'box' ? setGroup(e.target.value) : setX(e.target.value)} className="select w-full px-2 py-2 text-[13px]">
                  <option value="">— none —</option>
                  {cols.columns.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </Field>
            )}
            {['bar', 'line', 'area', 'scatter', 'box'].includes(type) && (
              <Field label="Y axis (numeric)" hint={type === 'scatter' || type === 'box' ? 'Required' : 'Empty = frequency count'}>
                <select value={y} onChange={(e) => setY(e.target.value)} className="select w-full px-2 py-2 text-[13px]">
                  <option value="">— none (count) —</option>
                  {cols.numeric.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </Field>
            )}
            {['bar', 'line', 'area', 'scatter'].includes(type) && (
              <Field label="Group by (optional)">
                <select value={group} onChange={(e) => setGroup(e.target.value)} className="select w-full px-2 py-2 text-[13px]">
                  <option value="">— none —</option>
                  {cols.categorical.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </Field>
            )}
            {['bar', 'line', 'area'].includes(type) && y && (
              <Field label="Aggregation">
                <select value={agg} onChange={(e) => setAgg(e.target.value)} className="select w-full px-2 py-2 text-[13px]">
                  {['mean', 'sum', 'median', 'min', 'max', 'count'].map((a) => <option key={a} value={a}>{a}</option>)}
                </select>
              </Field>
            )}
            {type === 'histogram' && (
              <Field label={`Bins (${bins})`}><input type="range" min={5} max={60} value={bins} onChange={(e) => setBins(Number(e.target.value))} className="w-full" /></Field>
            )}
            {['bar', 'line', 'area'].includes(type) && (
              <Field label={`Top categories (${topN})`}><input type="range" min={3} max={30} value={topN} onChange={(e) => setTopN(Number(e.target.value))} className="w-full" /></Field>
            )}
            <button onClick={build} disabled={busy} className="btn-moss w-full py-2 text-[13.5px] disabled:opacity-50">
              {busy ? 'Rendering…' : 'Build chart'}
            </button>
            <p className="text-[11.5px] text-muted leading-relaxed">
              Guidance: distributions → histogram/box · categories → bar · change over time → line/area ·
              two numbers → scatter · pies only for ≤ 12 categories.
            </p>
          </div>
        </Card>

        <div className="lg:col-span-3">
          <Card title={chart ? `${String(chart.type)} — live from your data` : 'Preview'} subtitle="Hover for values · use the camera icon to export PNG">
            {!chart && <div className="text-[13px] text-muted py-10 text-center">Configure a chart and press “Build chart”.</div>}
            {chart && <PlotView chart={chart} height={440} />}
            {chart && <CodeViewer code={String(chart.code || '')} title="View Python Code (matplotlib)" />}
          </Card>
        </div>
      </div>
    </div>
  );
}
