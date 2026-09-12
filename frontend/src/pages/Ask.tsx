import React, { useEffect, useState } from 'react';
import { api, fmt } from '../lib/api';
import { Card, PageHeader, Spinner, EmptyState, ErrorBox, CodeViewer } from '../components/ui';

type Msg = { q: string; a: string; kind: string; data: Record<string, unknown>[]; code: string };

const EXAMPLES = [
  'What is the average revenue?',
  'Which columns have missing values?',
  'What are the strongest correlations?',
  'Show me the monthly trend',
  'Find unusual records',
  'How many rows and columns?',
];

export default function Ask({ refreshToken }: { refreshToken: number }) {
  const [hasData, setHasData] = useState(true);
  const [q, setQ] = useState('');
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [ai, setAi] = useState<{ available: boolean; models: string[] }>({ available: false, models: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.allSettled([api.summary(), api.aiStatus()]).then(([s, a]) => {
      if (s.status === 'rejected' && String((s.reason as Error)?.message || '').includes('No dataset')) setHasData(false);
      if (a.status === 'fulfilled') setAi({ available: a.value.available, models: a.value.models || [] });
      setLoading(false);
    });
  }, [refreshToken]);

  const send = async (text: string) => {
    const question = text.trim();
    if (!question || busy) return;
    setBusy(true); setError(''); setQ('');
    try {
      const res = await api.ask(question);
      setMsgs((m) => [...m, { q: question, a: res.answer, kind: res.kind, data: res.data || [], code: res.code || '' }]);
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Failed'); }
    finally { setBusy(false); }
  };

  if (loading) return <Spinner label="Loading Ask Data…" />;
  if (!hasData) return <EmptyState title="No dataset loaded." body="Import a dataset first — then ask questions about it in plain English." />;

  return (
    <div className="page-enter max-w-3xl mx-auto">
      <PageHeader kicker="Ask Data" title="Ask Your Data" body="Questions are translated into real pandas operations on your dataset — never guessed. Local AI (Ollama) is optional, never required." />

      <div className={`card p-3 mb-3 text-[12.5px] flex items-center gap-2 ${ai.available ? '!border-moss' : ''}`}>
        <span className={`w-2 h-2 rounded-full ${ai.available ? 'bg-moss' : 'bg-line'}`} />
        {ai.available
          ? <>Local AI connected via Ollama ({ai.models.slice(0, 3).join(', ') || 'model ready'}). Core answers still run deterministically.</>
          : <>Core mode: deterministic analysis engine active. No local LLM detected — every answer below is computed, not generated.</>}
      </div>

      {error && <div className="mb-3"><ErrorBox message={error} /></div>}

      <div className="space-y-2.5 mb-3">
        {msgs.length === 0 && (
          <Card>
            <div className="text-[13px] text-muted mb-2.5">Try one of these:</div>
            <div className="flex flex-wrap gap-1.5">
              {EXAMPLES.map((e) => (
                <button key={e} onClick={() => send(e)} className="btn-ghost px-3 py-1.5 text-[12.5px] bg-white">“{e}”</button>
              ))}
            </div>
          </Card>
        )}
        {msgs.map((m, i) => (
          <div key={i}>
            <div className="flex justify-end mb-1.5">
              <div className="bg-ink text-surface text-[13px] px-4 py-2 rounded-[12px] rounded-br-[4px] max-w-[85%]">{m.q}</div>
            </div>
            <Card className="!p-4">
              <div className="text-[10.5px] uppercase tracking-[0.08em] text-bronze font-semibold mb-1">ORION · {m.kind}</div>
              <p className="text-[13.5px] leading-relaxed">{m.a}</p>
              {m.data.length > 0 && <DataTable rows={m.data} />}
              {m.code && <CodeViewer code={m.code} />}
            </Card>
          </div>
        ))}
        {busy && <Spinner label="Computing answer…" />}
      </div>

      <form onSubmit={(e) => { e.preventDefault(); send(q); }} className="flex gap-2 sticky bottom-4">
        <input
          value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="Ask about your data… e.g. What is the average salary?"
          className="input flex-1 px-4 py-3 text-[14px] shadow-card" aria-label="Ask a question"
        />
        <button type="submit" disabled={busy || !q.trim()} className="btn-primary px-5 text-[14px] disabled:opacity-50">Ask</button>
      </form>
    </div>
  );
}

function DataTable({ rows }: { rows: Record<string, unknown>[] }) {
  const keys = Object.keys(rows[0]).slice(0, 4);
  return (
    <div className="table-wrap overflow-auto max-h-[220px] border border-line rounded-[8px] mt-2.5">
      <table>
        <thead><tr>{keys.map((k) => <th key={k}>{k}</th>)}</tr></thead>
        <tbody>
          {rows.slice(0, 12).map((r, i) => (
            <tr key={i}>{keys.map((k) => <td key={k}>{typeof r[k] === 'number' ? fmt(r[k]) : String(r[k] ?? '—')}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
