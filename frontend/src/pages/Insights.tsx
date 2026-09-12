import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { Card, PageHeader, Spinner, EmptyState, ErrorBox } from '../components/ui';

type Insight = { kind: string; title: string; detail: string; columns: string[]; severity: string; metric: Record<string, unknown> };

const KIND_LABEL: Record<string, string> = {
  correlation: 'Correlation', missing: 'Missing data', dominance: 'Dominant category',
  distribution: 'Distribution', group_difference: 'Group difference', trend: 'Trend',
  outliers: 'Outliers', duplicates: 'Duplicates', identifier: 'Identifier',
};

export default function Insights({ refreshToken }: { refreshToken: number }) {
  const [data, setData] = useState<{ insights: Insight[]; count: number; note: string } | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true); setError('');
    try { setData(await api.insights()); }
    catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed';
      if (msg.includes('No dataset')) setData(null); else setError(msg);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [refreshToken]);

  if (loading) return <Spinner label="Mining insights from your data…" />;
  if (error) return <ErrorBox message={error} onRetry={load} />;
  if (!data) return <EmptyState title="No dataset loaded." body="Import a dataset and ORION will surface correlations, trends, and anomalies." />;

  return (
    <div className="page-enter">
      <PageHeader
        kicker="Insights" title="Automatic Insights"
        body={`${data.count} heuristic findings from your real data. ORION reports associations — never claims causation.`}
        action={<button onClick={load} className="btn-ghost px-4 py-2 text-[13px]">↻ Regenerate</button>}
      />
      <div className="explain-box rounded-[8px] px-4 py-2.5 text-[12.5px] mb-3">{data.note}</div>
      {data.insights.length === 0 && (
        <Card><div className="text-[13.5px]">No strong patterns stood out. Try a larger dataset or check Explore for manual analysis.</div></Card>
      )}
      <div className="grid md:grid-cols-2 gap-3">
        {data.insights.map((ins, i) => (
          <Card key={i} className="!p-4">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[10.5px] font-semibold uppercase tracking-[0.08em] px-2 py-0.5 rounded-full bg-ink text-surface">{KIND_LABEL[ins.kind] || ins.kind}</span>
              {ins.severity === 'warning' && <span className="text-[10.5px] font-semibold px-2 py-0.5 rounded-full sev-medium">⚠ review</span>}
              <span className="text-[11px] text-muted ml-auto">#{i + 1}</span>
            </div>
            <div className="font-serif text-[17px] font-medium leading-snug">{ins.title}</div>
            <p className="text-[12.5px] text-muted mt-1.5 leading-relaxed">{ins.detail}</p>
            {ins.columns.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {ins.columns.map((c) => <span key={c} className="text-[11.5px] font-mono bg-sand border border-line px-2 py-0.5 rounded">{c}</span>)}
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
