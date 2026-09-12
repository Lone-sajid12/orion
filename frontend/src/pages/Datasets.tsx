import React, { useEffect, useRef, useState } from 'react';
import { api, fmt } from '../lib/api';
import { Card, PageHeader, Spinner, ErrorBox, EmptyState, CodeViewer, Learn } from '../components/ui';

export default function Datasets({ onImported, refreshToken }: { onImported: () => void; refreshToken: number }) {
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [profile, setProfile] = useState<{ columns: ColProfile[] } | null>(null);
  const [preview, setPreview] = useState<PreviewState | null>(null);
  const [selected, setSelected] = useState<string>('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [drag, setDrag] = useState(false);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = async (p = 1, q = '') => {
    setLoading(true); setError('');
    try {
      const s = await api.summary();
      setSummary(s.summary);
      const prof = await api.profile();
      setProfile(prof);
      if (!selected && prof.columns.length) setSelected(prof.columns[0].name);
      const pv = await api.preview(p, 25, q);
      setPreview(pv);
      setPage(pv.page);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to load';
      if (msg.includes('No dataset')) { setSummary(null); setProfile(null); setPreview(null); }
      else setError(msg);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(1, ''); setSearch(''); }, [refreshToken]);

  const doUpload = async (f: File | undefined) => {
    if (!f) return;
    setUploading(true); setError('');
    try {
      await api.upload(f);
      onImported();
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Upload failed'); }
    finally { setUploading(false); }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDrag(false);
    const f = e.dataTransfer.files?.[0];
    if (f) doUpload(f);
  };

  if (loading) return <Spinner label="Inspecting dataset…" />;
  if (error) return <ErrorBox message={error} onRetry={() => load()} />;

  return (
    <div className="page-enter">
      <PageHeader
        kicker="Datasets"
        title="Dataset Explorer"
        body="Import CSV or Excel files, then inspect structure, types, and column profiles."
        action={
          <div className="flex gap-2">
            <button onClick={() => fileRef.current?.click()} className="btn-primary px-4 py-2 text-[13.5px]" disabled={uploading}>
              {uploading ? 'Importing…' : 'Import Dataset'}
            </button>
            <input
              ref={fileRef} type="file" accept=".csv,.xlsx,.xls,.xlsm" className="hidden"
              onChange={(e) => doUpload(e.target.files?.[0])} aria-label="Choose dataset file"
            />
          </div>
        }
      />

      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
        className={`card p-5 mb-4 border-dashed !border-2 text-center cursor-pointer transition-colors ${drag ? 'dropzone-drag' : ''}`}
        onClick={() => fileRef.current?.click()}
        role="button" tabIndex={0} aria-label="Drop a dataset file here or click to browse"
        onKeyDown={(e) => { if (e.key === 'Enter') fileRef.current?.click(); }}
      >
        <div className="text-[14px] font-semibold">Drag &amp; drop a .csv or .xlsx file here</div>
        <div className="text-[12.5px] text-muted mt-1">or click to browse · files stay on your computer · up to 250 MB</div>
      </div>

      {!summary && (
        <EmptyState
          title="No dataset loaded."
          body="Import a CSV or Excel file to inspect its structure — or start with the labelled sample to learn the workflow."
          action={
            <button
              onClick={async () => { setUploading(true); try { await api.loadSample(); onImported(); } finally { setUploading(false); } }}
              className="btn-ghost px-5 py-2.5 text-[14px]"
            >
              {uploading ? 'Loading…' : 'Load Sample Dataset'}
            </button>
          }
        />
      )}

      {summary && (
        <>
          <SummaryGrid s={summary} />
          <div className="grid lg:grid-cols-5 gap-3 mt-3">
            <Card title="Column explorer" subtitle="Select a column for its full profile" className="lg:col-span-2">
              <div className="max-h-[430px] overflow-y-auto -mx-1 px-1 space-y-1.5">
                {(profile?.columns || []).map((c) => (
                  <button
                    key={c.name}
                    onClick={() => setSelected(c.name)}
                    className={`w-full text-left px-3 py-2 rounded-[8px] border text-[13px] transition-colors ${selected === c.name ? 'border-ink bg-ink text-surface' : 'border-line bg-white hover:border-bronze'}`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium truncate">{c.name}</span>
                      <span className={`text-[10.5px] font-semibold px-1.5 py-0.5 rounded ${selected === c.name ? 'bg-panelsoft text-line' : 'bg-sand text-muted'}`}>{c.role}</span>
                    </div>
                    <div className={`text-[11.5px] mt-0.5 ${selected === c.name ? 'text-line/80' : 'text-muted'}`}>
                      {c.dtype} · {c.unique.toLocaleString()} unique · {c.missing_pct}% missing
                    </div>
                  </button>
                ))}
              </div>
            </Card>
            <div className="lg:col-span-3">
              {selected && <ColumnDetail name={selected} cached={(profile?.columns || []).find((c) => c.name === selected)} />}
            </div>
          </div>

          <Card
            title="Data preview" subtitle={preview ? `Page ${preview.page} of ${preview.total_pages} · ${fmt(preview.filtered_rows)} rows shown of ${fmt(preview.total_rows)}` : ''}
            className="mt-3"
            action={
              <div className="flex gap-2 items-center">
                <input
                  value={search} onChange={(e) => setSearch(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') load(1, search); }}
                  placeholder="Search all columns…" className="input px-3 py-1.5 text-[13px] w-[220px]" aria-label="Search rows"
                />
                <button onClick={() => load(1, search)} className="btn-ghost px-3 py-1.5 text-[12.5px]">Search</button>
              </div>
            }
          >
            {preview && (
              <>
                <div className="table-wrap overflow-auto max-h-[380px] border border-line rounded-[8px]">
                  <table>
                    <thead><tr>{preview.columns.map((c: string) => <th key={c}>{c}</th>)}</tr></thead>
                    <tbody>
                      {preview.rows.map((r: Record<string, unknown>, i: number) => (
                        <tr key={i}>
                          {preview.columns.map((c: string) => (
                            <td key={c} title={String(r[c] ?? '')}>{r[c] === null || r[c] === undefined ? <span className="text-muted italic">∅</span> : String(r[c])}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="flex items-center gap-2 mt-3 text-[13px]">
                  <button disabled={page <= 1} onClick={() => load(page - 1, search)} className="btn-ghost px-3 py-1 disabled:opacity-40">← Prev</button>
                  <span className="text-muted">Page {preview.page} / {preview.total_pages}</span>
                  <button disabled={page >= preview.total_pages} onClick={() => load(page + 1, search)} className="btn-ghost px-3 py-1 disabled:opacity-40">Next →</button>
                </div>
              </>
            )}
          </Card>
        </>
      )}
    </div>
  );
}

type ColProfile = {
  name: string; role: string; dtype: string; count: number; missing: number; missing_pct: number;
  unique: number; mean?: number | null; median?: number | null; std?: number | null;
  min?: unknown; max?: unknown; q1?: number | null; q3?: number | null; skew?: number | null;
  mode?: string; mode_count?: number;
  top_values?: { value: string; count: number; pct: number }[];
};

type PreviewState = {
  page: number; total_pages: number; filtered_rows: number; total_rows: number;
  columns: string[]; rows: Record<string, unknown>[];
};

function SummaryGrid({ s }: { s: Record<string, unknown> }) {
  const items: [string, string][] = [
    ['File', String(s.filename)],
    ['Shape', `${fmt(s.rows)} rows × ${fmt(s.columns)} cols`],
    ['Numeric', `${(s.numeric_columns as string[]).length} columns`],
    ['Categorical', `${(s.categorical_columns as string[]).length} columns`],
    ['Datetime', `${(s.datetime_columns as string[]).length} columns`],
    ['Missing', `${fmt(s.missing_cells)} cells (${s.missing_pct}%)`],
    ['Duplicates', `${fmt(s.duplicate_rows)} rows`],
    ['Memory', `~${s.memory_mb} MB`],
  ];
  return (
    <div className="card p-4 grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-2.5">
      {items.map(([k, v]) => (
        <div key={k} className="text-[13px]">
          <div className="text-[10.5px] uppercase tracking-[0.08em] text-muted font-semibold">{k}</div>
          <div className="font-medium truncate" title={v}>{v}</div>
        </div>
      ))}
    </div>
  );
}

function ColumnDetail({ name, cached }: { name: string; cached?: ColProfile }) {
  const [detail, setDetail] = useState<ColProfile | null>(cached || null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let live = true;
    setLoading(true);
    api.column(name).then((r) => { if (live) setDetail(r.profile); }).catch(() => { if (live) setDetail(cached || null); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name]);

  if (loading && !detail) return <Card title={name}><Spinner /></Card>;
  if (!detail) return null;
  const d = detail;
  const stats: [string, string][] = d.role === 'numeric'
    ? [['Mean', fmt(d.mean)], ['Median', fmt(d.median)], ['Std dev', fmt(d.std)], ['Min', fmt(d.min)], ['Q1', fmt(d.q1)], ['Q3', fmt(d.q3)], ['Max', fmt(d.max)], ['Skew', fmt(d.skew)]]
    : [['Unique', fmt(d.unique)], ['Mode', d.mode || '—'], ['Mode count', fmt(d.mode_count)], ['Min', String(d.min ?? '—')], ['Max', String(d.max ?? '—')]];

  return (
    <Card title={d.name} subtitle={`${d.role} · ${d.dtype} · ${fmt(d.count)} non-null · ${d.missing_pct}% missing`}>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {stats.map(([k, v]) => (
          <div key={k} className="bg-white border border-line rounded-[8px] px-3 py-2">
            <div className="text-[10.5px] uppercase tracking-[0.06em] text-muted font-semibold">{k}</div>
            <div className="text-[14px] font-semibold truncate" title={v}>{v}</div>
          </div>
        ))}
      </div>
      {d.top_values && d.top_values.length > 0 && (
        <div className="mt-3">
          <div className="text-[12px] font-semibold mb-1.5">Most frequent values</div>
          <div className="space-y-1">
            {d.top_values.slice(0, 8).map((t, i) => (
              <div key={i} className="flex items-center gap-2 text-[12.5px]">
                <span className="w-[180px] truncate shrink-0" title={t.value}>{t.value}</span>
                <div className="flex-1 h-2 bg-sand rounded-full overflow-hidden">
                  <div className="h-full bg-moss rounded-full" style={{ width: `${Math.min(100, t.pct * 3)}%` }} />
                </div>
                <span className="text-muted w-[110px] text-right shrink-0">{fmt(t.count)} · {t.pct}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
      <Learn title="column profiles">
        A profile tells you what a column <em>can</em> do: numeric columns with wide ranges suit regression and distributions;
        low-cardinality text suits grouping and classification. High missingness or a single repeated value is a warning sign —
        check the Quality Center before modelling.
      </Learn>
      <CodeViewer code={'import pandas as pd\ncol = df[' + JSON.stringify(d.name) + ']\nprint(col.describe(include="all"))\nprint("missing:", col.isna().sum(), "| unique:", col.nunique())\nprint(col.value_counts(dropna=False).head(10))\n'} />
    </Card>
  );
}
