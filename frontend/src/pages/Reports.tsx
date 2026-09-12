import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { Card, PageHeader, Spinner, EmptyState, ErrorBox, CodeViewer } from '../components/ui';

export default function Reports({ refreshToken }: { refreshToken: number }) {
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [codes, setCodes] = useState<{ label: string; code: string; at: string }[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true); setError('');
    try {
      const [r, c] = await Promise.all([api.report(), api.codeLog()]);
      setReport(r); setCodes(c.entries || []);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed';
      if (msg.includes('No dataset')) setReport(null); else setError(msg);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [refreshToken]);

  const download = (format: 'html' | 'markdown', filename: string) => {
    const a = document.createElement('a');
    a.href = api.reportUrl(format);
    a.download = filename;
    a.target = '_blank';
    a.click();
  };

  if (loading) return <Spinner label="Compiling report…" />;
  if (error) return <ErrorBox message={error} onRetry={load} />;
  if (!report) return <EmptyState title="No dataset loaded." body="Import and analyze a dataset, then generate a professional report." />;

  const s = report.summary as Record<string, unknown>;

  return (
    <div className="page-enter">
      <PageHeader
        kicker="Reports" title="Analysis Report"
        body="A professional summary of your dataset, quality findings, insights, and models — ready as a learning artifact."
        action={
          <div className="flex gap-2">
            <button onClick={() => download('html', 'orion_report.html')} className="btn-primary px-4 py-2 text-[13px]">Download HTML</button>
            <button onClick={() => download('markdown', 'orion_report.md')} className="btn-ghost px-4 py-2 text-[13px]">Download Markdown</button>
            <button onClick={load} className="btn-ghost px-4 py-2 text-[13px]">↻ Regenerate</button>
          </div>
        }
      />

      <div className="grid lg:grid-cols-3 gap-3">
        <div className="lg:col-span-2">
          <Card title={String(s.filename)} subtitle={`Quality score ${report.quality_score}/100 · ${String(s.rows)} rows × ${String(s.columns)} columns`}>
            <pre className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed max-h-[560px] overflow-y-auto bg-white border border-line rounded-[8px] p-4">
              {String(report.markdown).slice(0, 12000)}
            </pre>
          </Card>
        </div>
        <div>
          <Card title="Python code journal" subtitle="Every major step, reproducible">
            {codes.length === 0 && <div className="text-[13px] text-muted">Cleaning and ML operations will log their Python here.</div>}
            <div className="space-y-2 max-h-[560px] overflow-y-auto pr-1">
              {codes.map((c, i) => (
                <div key={i} className="border border-line rounded-[8px] p-3 bg-white">
                  <div className="text-[12.5px] font-semibold">{c.label}</div>
                  <CodeViewer code={c.code} title="Code" />
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
