import React, { useEffect, useState } from 'react';
import { api, fmt } from '../lib/api';
import { Card, Stat, EmptyState, Spinner, ErrorBox, PageHeader } from '../components/ui';
import type { NavKey } from '../components/Sidebar';

export default function Dashboard({ onNav, refreshToken, onImported }: {
  onNav: (k: NavKey) => void; refreshToken: number; onImported: () => void;
}) {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);

  const load = async () => {
    setLoading(true); setError('');
    try {
      const res = await api.summary();
      setData(res);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to load';
      if (msg.includes('No dataset')) { setData(null); }
      else setError(msg);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [refreshToken]);

  const sample = async () => {
    setImporting(true);
    try {
      await api.loadSample();
      onImported();
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Failed'); }
    finally { setImporting(false); }
  };

  if (loading) return <Spinner label="Loading workspace…" />;
  if (error) return <ErrorBox message={error} onRetry={load} />;

  if (!data) {
    return (
      <div className="page-enter max-w-3xl mx-auto pt-8">
        <div className="text-center mb-8">
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-bronze">ORION · Personal Data Workstation</div>
          <h1 className="font-serif text-[44px] leading-[1.05] font-medium tracking-tight mt-3">Turn Data Into<br />Decisions.</h1>
          <p className="text-muted text-[15px] mt-3">Welcome back, Sajid. Your analysis workspace is ready.</p>
        </div>
        <EmptyState
          title="Your analysis workspace is ready."
          body="Import a dataset to begin exploring, cleaning, visualizing, and modeling your data. Everything runs locally on your computer — no database, no API keys, no uploads."
          action={
            <div className="flex gap-2.5 justify-center">
              <button onClick={() => onNav('datasets')} className="btn-primary px-5 py-2.5 text-[14px]">Import Dataset</button>
              <button onClick={sample} disabled={importing} className="btn-ghost px-5 py-2.5 text-[14px]">
                {importing ? 'Loading…' : 'Try Sample Dataset'}
              </button>
            </div>
          }
        />
        <div className="grid grid-cols-3 gap-3 mt-6">
          {[
            ['Local-first', 'Datasets stay on your computer.'],
            ['Deterministic', 'Real pandas / sklearn analysis.'],
            ['Learning-first', 'Every step shows its Python.'],
          ].map(([t, b]) => (
            <div key={t} className="card p-4 text-center">
              <div className="text-[13px] font-semibold">{t}</div>
              <div className="text-[12px] text-muted mt-1">{b}</div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const s = data.summary as Record<string, unknown>;
  const log = (data.analysis_log as { kind: string; label: string; at: string }[]) || [];

  const quickActions: { key: NavKey; label: string; desc: string }[] = [
    { key: 'datasets', label: 'Import Dataset', desc: 'CSV & Excel' },
    { key: 'datasets', label: 'Explore Dataset', desc: 'Profile & preview' },
    { key: 'quality', label: 'Clean Data', desc: 'Fix quality issues' },
    { key: 'visualize', label: 'Visualize', desc: 'Build charts' },
    { key: 'statistics', label: 'Analyze', desc: 'Stats & tests' },
    { key: 'ml', label: 'Machine Learning', desc: 'Train & predict' },
  ];

  return (
    <div className="page-enter">
      <PageHeader
        kicker="Dashboard"
        title="Turn Data Into Decisions."
        body={`Welcome back, Sajid — currently working on ${(s.filename as string) || 'your dataset'}.`}
      />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Rows" value={fmt(s.rows)} sub={`${fmt(s.columns)} columns`} />
        <Stat label="Numeric" value={(s.numeric_columns as string[]).length} sub={`${(s.categorical_columns as string[]).length} categorical · ${(s.datetime_columns as string[]).length} datetime`} />
        <Stat label="Missing cells" value={fmt(s.missing_cells)} sub={`${s.missing_pct}% of all cells`} />
        <Stat label="Duplicates" value={fmt(s.duplicate_rows)} sub={`${s.duplicate_pct}% of rows`} accent />
      </div>

      <div className="grid md:grid-cols-3 gap-3 mt-4">
        <Card title="Quick actions" subtitle="Jump into a workflow" className="md:col-span-2">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5">
            {quickActions.map((a, i) => (
              <button key={i} onClick={() => onNav(a.key)} className="btn-ghost p-3.5 text-left bg-white">
                <div className="text-[13.5px] font-semibold">{a.label}</div>
                <div className="text-[12px] text-muted">{a.desc}</div>
              </button>
            ))}
          </div>
        </Card>
        <Card title="Recent analysis" subtitle="This session, newest first">
          {log.length === 0 && <div className="text-[13px] text-muted">No analysis yet — your history will appear here.</div>}
          <ul className="space-y-2 max-h-[240px] overflow-y-auto">
            {log.map((e, i) => (
              <li key={i} className="text-[12.5px] flex gap-2">
                <span className="text-bronze font-semibold shrink-0 w-[52px]">{e.kind}</span>
                <span className="truncate" title={e.label}>{e.label}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="grid md:grid-cols-2 gap-3 mt-3">
        <Card title="Dataset" subtitle="File under analysis">
          <div className="text-[13px] space-y-1.5">
            <Row k="File" v={String(s.filename)} />
            <Row k="Shape" v={`${fmt(s.rows)} rows × ${fmt(s.columns)} columns`} />
            <Row k="Memory" v={`~${s.memory_mb} MB in memory`} />
            <Row k="Types" v={`${(s.numeric_columns as string[]).length} num · ${(s.categorical_columns as string[]).length} cat · ${(s.datetime_columns as string[]).length} date · ${(s.boolean_columns as string[]).length} bool`} />
          </div>
        </Card>
        <Card title="Data health" subtitle="At a glance" action={<button onClick={() => onNav('quality')} className="btn-ghost px-3 py-1.5 text-[12.5px]">Open Quality Center →</button>}>
          <HealthBar missing={Number(s.missing_pct)} dups={Number(s.duplicate_pct)} />
        </Card>
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex gap-2">
      <span className="text-muted w-[70px] shrink-0">{k}</span>
      <span className="font-medium truncate" title={v}>{v}</span>
    </div>
  );
}

function HealthBar({ missing, dups }: { missing: number; dups: number }) {
  const score = Math.max(5, Math.min(100, 100 - Math.min(35, missing * 1.2) - Math.min(15, dups * 2)));
  const color = score >= 85 ? '#66745A' : score >= 65 ? '#A68A64' : '#8C3B2E';
  return (
    <div>
      <div className="flex items-baseline gap-2">
        <span className="font-serif text-[34px] font-medium">{score.toFixed(0)}</span>
        <span className="text-muted text-[13px]">/ 100 estimated quality</span>
      </div>
      <div className="h-2.5 rounded-full bg-line mt-2 overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${score}%`, background: color }} />
      </div>
      <p className="text-[12.5px] text-muted mt-2">Missing cells {missing}% · duplicate rows {dups}%. Full breakdown in the Quality Center.</p>
    </div>
  );
}
