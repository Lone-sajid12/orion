import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { Card, PageHeader, Spinner } from '../components/ui';

export default function Settings() {
  const [ai, setAi] = useState<{ available: boolean; models: string[] } | null>(null);
  const [compact, setCompact] = useState(localStorage.getItem('orion_compact') === '1');

  useEffect(() => {
    api.aiStatus().then(setAi).catch(() => setAi({ available: false, models: [] }));
  }, []);

  const toggleCompact = () => {
    const v = !compact;
    setCompact(v);
    localStorage.setItem('orion_compact', v ? '1' : '0');
  };

  return (
    <div className="page-enter max-w-3xl">
      <PageHeader kicker="Settings" title="Profile & Settings" body="Lightweight preferences only — ORION uses no database and stores no datasets in the browser." />

      <Card title="Sajid Jamal" subtitle="Computer Science Student · Data Analysis → Data Science → AI/ML">
        <p className="text-[13.5px] leading-relaxed text-ink/90">
          ORION — <em>Turn Data Into Decisions</em> — is your personal data workstation, created for Sajid Jamal.
          Import real datasets, learn each technique with its Python code, and build portfolio-ready analysis.
        </p>
      </Card>

      <Card title="Local AI (optional)" subtitle="Ollama-compatible · never required" className="mt-3">
        {!ai && <Spinner label="Probing localhost:11434…" />}
        {ai && (
          <div className="text-[13.5px]">
            <div className="flex items-center gap-2">
              <span className={`w-2.5 h-2.5 rounded-full ${ai.available ? 'bg-moss' : 'bg-line'}`} />
              <b>{ai.available ? 'Connected' : 'Not detected — Core Mode active'}</b>
            </div>
            {ai.available && ai.models.length > 0 && (
              <div className="text-muted mt-1">Models: {ai.models.join(', ')}</div>
            )}
            <div className="bg-white border border-line rounded-[8px] p-3.5 mt-3 text-[12.5px] leading-relaxed">
              <b>Enable local AI:</b>
              <ol className="list-decimal ml-5 mt-1.5 space-y-1">
                <li>Install Ollama from <span className="font-mono">ollama.com</span></li>
                <li>Run <span className="font-mono bg-sand px-1.5 py-0.5 rounded">ollama pull llama3.1</span> then <span className="font-mono bg-sand px-1.5 py-0.5 rounded">ollama serve</span></li>
                <li>Return here — ORION detects it automatically. Core analysis works identically with or without it.</li>
              </ol>
            </div>
          </div>
        )}
      </Card>

      <Card title="Preferences" subtitle="Stored in browser localStorage only" className="mt-3">
        <label className="flex items-center gap-2.5 text-[13.5px] cursor-pointer">
          <input type="checkbox" checked={compact} onChange={toggleCompact} className="accent-[#66745A] w-4 h-4" />
          Compact sidebar (icons only)
        </label>
        <p className="text-[12px] text-muted mt-2">ORION never stores datasets in localStorage. Preferences are limited to theme and UI choices.</p>
      </Card>

      <Card title="Privacy" subtitle="Local-first, always" className="mt-3">
        <p className="text-[13.5px] leading-relaxed">
          “Your datasets stay on your computer unless you explicitly configure an external service.”
          No analytics, no tracking, no cloud uploads. The only network call ORION ever makes is an optional
          one to <span className="font-mono">localhost:11434</span> if you install Ollama yourself.
        </p>
      </Card>

      <Card title="About ORION" subtitle="v1.0.0 · portfolio-grade local workstation" className="mt-3">
        <div className="text-[13px] text-muted leading-relaxed">
          Engine: Python · pandas · NumPy · SciPy · scikit-learn · openpyxl · FastAPI<br />
          Interface: React · TypeScript · Tailwind · Plotly<br />
          No external API key is required for core functionality. No database is required.
        </div>
      </Card>
    </div>
  );
}
