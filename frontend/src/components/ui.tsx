import React, { useState } from 'react';

export function Card({ children, className = '', title, subtitle, action }: {
  children: React.ReactNode; className?: string; title?: string; subtitle?: string; action?: React.ReactNode;
}) {
  return (
    <div className={`card p-5 ${className}`}>
      {(title || action) && (
        <div className="flex items-start justify-between gap-3 mb-3">
          <div>
            {title && <h3 className="text-[15px] font-semibold tracking-tight">{title}</h3>}
            {subtitle && <p className="text-[12.5px] text-muted mt-0.5">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </div>
  );
}

export function Stat({ label, value, sub, accent }: { label: string; value: React.ReactNode; sub?: string; accent?: boolean }) {
  return (
    <div className={`card px-4 py-3.5 ${accent ? 'bg-panel text-[#F3EFE6] !border-panel' : ''}`}>
      <div className={`text-[11px] font-semibold uppercase tracking-[0.08em] ${accent ? 'text-[#B9B7AC]' : 'text-muted'}`}>{label}</div>
      <div className="text-[22px] font-semibold tracking-tight mt-1 font-serif">{value}</div>
      {sub && <div className={`text-[12px] mt-0.5 ${accent ? 'text-[#B9B7AC]' : 'text-muted'}`}>{sub}</div>}
    </div>
  );
}

export function EmptyState({ title, body, action }: { title: string; body: string; action?: React.ReactNode }) {
  return (
    <div className="card p-10 text-center max-w-xl mx-auto">
      <div className="mx-auto w-12 h-12 rounded-xl bg-panel flex items-center justify-center mb-4">
        <svg width="24" height="24" viewBox="0 0 32 32" aria-hidden="true">
          <circle cx="11" cy="12" r="2.4" fill="#F3EFE6" />
          <circle cx="21" cy="10" r="1.6" fill="#A68A64" />
          <circle cx="16" cy="20" r="2.8" fill="#66745A" />
        </svg>
      </div>
      <h3 className="font-serif text-[22px] font-medium">{title}</h3>
      <p className="text-muted text-[13.5px] mt-2 leading-relaxed">{body}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function Spinner({ label = 'Working…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-2.5 text-muted text-[13px] loading-pulse py-6 justify-center" role="status">
      <span className="w-4 h-4 rounded-full border-2 border-line border-t-moss inline-block" style={{ animation: 'spin 0.9s linear infinite' }} />
      {label}
      <style>{'@keyframes spin{to{transform:rotate(360deg)}}'}</style>
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-[10px] border border-[#D9A79B] bg-[#F7E9E5] p-4 text-[13px] text-[#8C3B2E]">
      <div className="font-semibold">Something needs attention</div>
      <div className="mt-1">{message}</div>
      {onRetry && (
        <button onClick={onRetry} className="btn-ghost px-3 py-1.5 text-[12.5px] mt-2.5 bg-white">Try again</button>
      )}
    </div>
  );
}

export function Learn({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen(!open)}
        className="text-[12.5px] text-moss font-medium hover:underline focus:underline"
        aria-expanded={open}
      >
        {open ? '▾' : '▸'} Why does this matter? — {title}
      </button>
      {open && <div className="explain-box rounded-r-[8px] px-3.5 py-2.5 mt-1.5 text-[12.5px] leading-relaxed text-ink/90">{children}</div>}
    </div>
  );
}

export function CodeViewer({ code, title = 'View Python Code', downloadable = true }: {
  code: string; title?: string; downloadable?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  if (!code) return null;
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch { /* clipboard unavailable */ }
  };
  const download = () => {
    const blob = new Blob([code], { type: 'text/x-python' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'orion_analysis.py';
    a.click();
    URL.revokeObjectURL(a.href);
  };
  return (
    <div className="mt-3">
      <button onClick={() => setOpen(!open)} className="btn-ghost px-3 py-1.5 text-[12.5px]" aria-expanded={open}>
        {open ? '▾ Hide' : '▸'} {title}
      </button>
      {open && (
        <div className="mt-2">
          <div className="flex gap-2 mb-2">
            <button onClick={copy} className="btn-ghost px-3 py-1 text-[12px] bg-white">{copied ? 'Copied ✓' : 'Copy code'}</button>
            {downloadable && <button onClick={download} className="btn-ghost px-3 py-1 text-[12px] bg-white">Download .py</button>}
          </div>
          <pre className="code-block p-4 overflow-x-auto whitespace-pre">{code}</pre>
        </div>
      )}
    </div>
  );
}

export function PageHeader({ kicker, title, body, action }: {
  kicker: string; title: string; body?: string; action?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 mb-5">
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-bronze">{kicker}</div>
        <h1 className="font-serif text-[30px] leading-tight font-medium tracking-tight mt-1">{title}</h1>
        {body && <p className="text-muted text-[13.5px] mt-1 max-w-2xl leading-relaxed">{body}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function Field({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="text-[12px] font-semibold text-ink/80">{label}</span>
      <div className="mt-1">{children}</div>
      {hint && <span className="text-[11.5px] text-muted">{hint}</span>}
    </label>
  );
}

export function SeverityBadge({ level }: { level: string }) {
  const cls = level === 'high' ? 'sev-high' : level === 'medium' ? 'sev-medium' : 'sev-low';
  return <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${cls}`}>{level}</span>;
}
