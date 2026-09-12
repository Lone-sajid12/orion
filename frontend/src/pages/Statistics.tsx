import React, { useEffect, useState } from 'react';
import { api, fmt } from '../lib/api';
import { Card, PageHeader, Spinner, EmptyState, ErrorBox, CodeViewer, Learn, Field } from '../components/ui';

type Tab = 'describe' | 'corr' | 'ci' | 'ttest' | 'chi2' | 'anova';

export default function Statistics({ refreshToken }: { refreshToken: number }) {
  const [cols, setCols] = useState<{ columns: string[]; numeric: string[]; categorical: string[]; datetime: string[] } | null>(null);
  const [tab, setTab] = useState<Tab>('describe');
  const [out, setOut] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  // form state
  const [cx, setCx] = useState(''); const [cy, setCy] = useState(''); const [cm, setCm] = useState('pearson');
  const [ciCol, setCiCol] = useState(''); const [level, setLevel] = useState(0.95);
  const [tNum, setTNum] = useState(''); const [tGrp, setTGrp] = useState('');
  const [cA, setCA] = useState(''); const [cB, setCB] = useState('');
  const [aNum, setANum] = useState(''); const [aGrp, setAGrp] = useState('');

  useEffect(() => {
    setLoading(true);
    api.columns()
      .then((c) => {
        setCols(c);
        setCx(c.numeric[0] || ''); setCy(c.numeric[1] || c.numeric[0] || '');
        setCiCol(c.numeric[0] || '');
        setTNum(c.numeric[0] || ''); setTGrp(c.categorical[0] || '');
        setCA(c.categorical[0] || ''); setCB(c.categorical[1] || c.categorical[0] || '');
        setANum(c.numeric[0] || ''); setAGrp(c.categorical[0] || '');
      })
      .then(() => api.statsDescriptive().then(setOut).catch((e: unknown) => setError(e instanceof Error ? e.message : '')))
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : 'Failed';
        if (!msg.includes('No dataset')) setError(msg);
      })
      .finally(() => setLoading(false));
  }, [refreshToken]);

  const run = async (fn: () => Promise<Record<string, unknown>>) => {
    setBusy(true); setError(''); setOut(null);
    try { setOut(await fn()); } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Test failed'); }
    finally { setBusy(false); }
  };

  if (loading) return <Spinner label="Loading Statistics Lab…" />;
  if (!cols) return <EmptyState title="No dataset loaded." body="Import a dataset to run descriptive statistics and hypothesis tests." />;

  const tabs: [Tab, string, string][] = [
    ['describe', 'Descriptive', 'Means, spreads, percentiles'],
    ['corr', 'Correlation', 'Pearson / Spearman / Kendall'],
    ['ci', 'Confidence Interval', 'Mean with uncertainty'],
    ['ttest', 't-Test', 'Compare 2 group means'],
    ['chi2', 'Chi-Square', 'Categorical independence'],
    ['anova', 'ANOVA', 'Compare 3+ group means'],
  ];

  return (
    <div className="page-enter">
      <PageHeader kicker="Statistics" title="Statistics Lab" body="Learn inference on your own data. Every result pairs the statistic with a plain-language explanation." />
      <div className="flex flex-wrap gap-1.5 mb-3">
        {tabs.map(([k, label, sub]) => (
          <button
            key={k}
            onClick={() => { setTab(k); setOut(null); setError(''); if (k === 'describe') run(() => api.statsDescriptive()); }}
            className={`px-3.5 py-2 rounded-[8px] border text-left ${tab === k ? 'bg-ink text-surface border-ink' : 'bg-surface border-line hover:border-bronze'}`}
          >
            <span className="block text-[13px] font-semibold">{label}</span>
            <span className={`block text-[11px] ${tab === k ? 'text-line' : 'text-muted'}`}>{sub}</span>
          </button>
        ))}
      </div>

      {error && <div className="mb-3"><ErrorBox message={error} /></div>}

      <div className="grid lg:grid-cols-3 gap-3">
        <Card title="Setup" subtitle="Choose inputs, then run">
          {tab === 'describe' && (
            <div className="text-[13px] text-muted">Uses all numeric columns.<br /><button onClick={() => run(() => api.statsDescriptive())} className="btn-moss px-4 py-2 text-[13px] mt-3">Run descriptives</button></div>
          )}
          {tab === 'corr' && (
            <div className="space-y-3">
              <Field label="X (numeric)"><Select val={cx} set={setCx} opts={cols.numeric} /></Field>
              <Field label="Y (numeric)"><Select val={cy} set={setCy} opts={cols.numeric} /></Field>
              <Field label="Method"><select value={cm} onChange={(e) => setCm(e.target.value)} className="select w-full px-2 py-2 text-[13px]"><option value="pearson">Pearson</option><option value="spearman">Spearman</option><option value="kendall">Kendall</option></select></Field>
              <Go busy={busy} onClick={() => run(() => api.statsCorr(cx, cy, cm))} />
            </div>
          )}
          {tab === 'ci' && (
            <div className="space-y-3">
              <Field label="Column (numeric)"><Select val={ciCol} set={setCiCol} opts={cols.numeric} /></Field>
              <Field label={`Confidence level (${Math.round(level * 100)}%)`}><input type="range" min={80} max={99} value={Math.round(level * 100)} onChange={(e) => setLevel(Number(e.target.value) / 100)} className="w-full" /></Field>
              <Go busy={busy} onClick={() => run(() => api.statsCI(ciCol, level))} />
            </div>
          )}
          {tab === 'ttest' && (
            <div className="space-y-3">
              <Field label="Numeric column"><Select val={tNum} set={setTNum} opts={cols.numeric} /></Field>
              <Field label="Group column"><Select val={tGrp} set={setTGrp} opts={cols.categorical} /></Field>
              <Go busy={busy} label="Run t-test" onClick={() => run(() => api.statsTTest(tNum, tGrp))} />
              <p className="text-[11.5px] text-muted">Compares the two largest groups (Welch's t-test, no equal-variance assumption).</p>
            </div>
          )}
          {tab === 'chi2' && (
            <div className="space-y-3">
              <Field label="Column A (categorical)"><Select val={cA} set={setCA} opts={cols.categorical} /></Field>
              <Field label="Column B (categorical)"><Select val={cB} set={setCB} opts={cols.categorical} /></Field>
              <Go busy={busy} label="Run chi-square" onClick={() => run(() => api.statsChi2(cA, cB))} />
            </div>
          )}
          {tab === 'anova' && (
            <div className="space-y-3">
              <Field label="Numeric column"><Select val={aNum} set={setANum} opts={cols.numeric} /></Field>
              <Field label="Group column"><Select val={aGrp} set={setAGrp} opts={cols.categorical} /></Field>
              <Go busy={busy} label="Run ANOVA" onClick={() => run(() => api.statsAnova(aNum, aGrp))} />
            </div>
          )}
        </Card>

        <div className="lg:col-span-2">
          {busy && <Card><Spinner /></Card>}
          {!busy && !out && !error && <Card><div className="text-[13px] text-muted">Configure the test and press Run.</div></Card>}
          {out && tab === 'describe' && <DescribeOut data={out} />}
          {out && tab !== 'describe' && <TestOut data={out} />}
        </div>
      </div>
    </div>
  );
}

function Select({ val, set, opts }: { val: string; set: (v: string) => void; opts: string[] }) {
  return (
    <select value={val} onChange={(e) => set(e.target.value)} className="select w-full px-2 py-2 text-[13px]">
      {opts.length === 0 && <option value="">— no suitable columns —</option>}
      {opts.map((c) => <option key={c} value={c}>{c}</option>)}
    </select>
  );
}

function Go({ busy, onClick, label = 'Run test' }: { busy: boolean; onClick: () => void; label?: string }) {
  return <button onClick={onClick} disabled={busy} className="btn-moss px-4 py-2 text-[13px] disabled:opacity-50 w-full">{busy ? 'Running…' : label}</button>;
}

function DescribeOut({ data }: { data: Record<string, unknown> }) {
  const rows = data.rows as Record<string, unknown>[];
  return (
    <Card title="Descriptive statistics" subtitle="Count, center, spread, shape — per numeric column">
      <div className="table-wrap overflow-auto max-h-[420px] border border-line rounded-[8px]">
        <table>
          <thead><tr>{['column', 'count', 'mean', 'std', 'min', 'q1', 'median', 'q3', 'max', 'skew'].map((h) => <th key={h}>{h}</th>)}</tr></thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td className="!font-semibold">{String(r.column)}</td>
                <td>{fmt(r.count)}</td><td>{fmt(r.mean)}</td><td>{fmt(r.std)}</td><td>{fmt(r.min)}</td>
                <td>{fmt(r.q1)}</td><td>{fmt(r.median)}</td><td>{fmt(r.q3)}</td><td>{fmt(r.max)}</td><td>{fmt(r.skew)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Learn title="descriptive statistics">
        <b>Mean</b> is the balance point; <b>median</b> is the middle value and resists outliers. <b>Std dev</b> measures
        typical spread. <b>Skew</b> beyond ±1 means a long tail — the median then describes “typical” better than the mean.
      </Learn>
      <CodeViewer code={String(data.code || '')} />
    </Card>
  );
}

function TestOut({ data }: { data: Record<string, unknown> }) {
  const p = data.p_value as number | null;
  const sig = p !== null && p !== undefined && p < 0.05;
  const statRows = Object.entries(data)
    .filter(([k]) => !['explanation', 'code', 'groups', 'groups_available'].includes(k))
    .map(([k, v]) => [k, typeof v === 'number' ? fmt(v) : Array.isArray(v) ? `${v.length} items` : String(v ?? '—')] as [string, string]);

  return (
    <Card
      title="Result"
      subtitle={sig ? 'Significant at α = 0.05' : p === null || p === undefined ? 'See explanation' : 'Not significant at α = 0.05'}
      action={<span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full ${sig ? 'bg-moss text-surface' : 'bg-sand text-muted border border-line'}`}>{sig ? '● significant' : '○ not significant'}</span>}
    >
      <div className="grid grid-cols-2 md:grid-cols-3 gap-1.5">
        {statRows.map(([k, v]) => (
          <div key={k} className="bg-white border border-line rounded-[8px] px-2.5 py-1.5">
            <div className="text-[10px] uppercase tracking-[0.06em] text-muted font-semibold">{k}</div>
            <div className="text-[13px] font-semibold truncate" title={v}>{v}</div>
          </div>
        ))}
      </div>
      {Array.isArray(data.groups) && (
        <div className="mt-3 text-[12.5px]">
          <div className="font-semibold mb-1">Group means</div>
          {(data.groups as { group: string; mean: number; n: number }[]).map((g, i) => (
            <div key={i} className="flex justify-between border-b border-line/60 py-1">
              <span>{g.group} (n={g.n})</span><span className="font-semibold">{fmt(g.mean)}</span>
            </div>
          ))}
        </div>
      )}
      <div className="explain-box rounded-r-[8px] px-3.5 py-2.5 mt-3 text-[13px] leading-relaxed">
        {String(data.explanation || '')}
      </div>
      <Learn title="p-values">
        A p-value is the probability of seeing a result this extreme <em>if there were truly no effect</em>.
        p &lt; 0.05 is the conventional “significant” threshold — but significance is not importance, and it never proves causation.
        Always check effect size (the actual difference) alongside p.
      </Learn>
      <CodeViewer code={String(data.code || '')} />
    </Card>
  );
}
