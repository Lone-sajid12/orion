import React from 'react';

export type NavKey = 'dashboard' | 'datasets' | 'quality' | 'explore' | 'visualize' | 'statistics' | 'insights' | 'ml' | 'ask' | 'reports' | 'settings';

const ITEMS: { key: NavKey; label: string; sub: string; icon: string }[] = [
  { key: 'dashboard', label: 'Dashboard', sub: 'Overview', icon: '◧' },
  { key: 'datasets', label: 'Datasets', sub: 'Import & explore', icon: '▦' },
  { key: 'quality', label: 'Data Quality', sub: 'Issues & cleaning', icon: '✓' },
  { key: 'explore', label: 'Explore', sub: 'EDA workspace', icon: '◐' },
  { key: 'visualize', label: 'Visualize', sub: 'Chart builder', icon: '▭' },
  { key: 'statistics', label: 'Statistics', sub: 'Tests & inference', icon: 'σ' },
  { key: 'insights', label: 'Insights', sub: 'Auto findings', icon: '✦' },
  { key: 'ml', label: 'Machine Learning', sub: 'Train & predict', icon: '⬡' },
  { key: 'ask', label: 'Ask Data', sub: 'Natural language', icon: '?' },
  { key: 'reports', label: 'Reports', sub: 'Export results', icon: '≡' },
  { key: 'settings', label: 'Settings', sub: 'Profile & AI', icon: '⚙' },
];

export default function Sidebar({ active, onNav, hasData, filename, collapsed }: {
  active: NavKey; onNav: (k: NavKey) => void; hasData: boolean; filename?: string; collapsed: boolean;
}) {
  return (
    <aside
      className={`shrink-0 bg-surface border-r border-line flex flex-col h-full ${collapsed ? 'w-[64px]' : 'w-[248px]'}`}
      aria-label="Primary navigation"
    >
      <div className="px-4 pt-5 pb-4 border-b border-line">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-[9px] bg-panel flex items-center justify-center shrink-0" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 32 32">
              <circle cx="11" cy="12" r="2.4" fill="#F3EFE6" />
              <circle cx="21" cy="10" r="1.6" fill="#A68A64" />
              <circle cx="16" cy="20" r="2.8" fill="#66745A" />
            </svg>
          </div>
          {!collapsed && (
            <div>
              <div className="font-serif text-[19px] font-semibold tracking-tight leading-none">ORION</div>
              <div className="text-[10.5px] text-muted mt-1 tracking-wide">Turn Data Into Decisions.</div>
            </div>
          )}
        </div>
      </div>

      {!collapsed && (
        <div className="px-4 py-3 border-b border-line">
          {hasData ? (
            <div className="text-[12px]">
              <div className="text-muted text-[10.5px] uppercase tracking-[0.1em] font-semibold">Current dataset</div>
              <div className="font-medium truncate mt-0.5" title={filename}>{filename}</div>
            </div>
          ) : (
            <div className="text-[12px] text-muted">No dataset loaded.<br />Import one to begin.</div>
          )}
        </div>
      )}

      <nav className="flex-1 overflow-y-auto py-2" aria-label="Sections">
        {ITEMS.map((it) => (
          <button
            key={it.key}
            onClick={() => onNav(it.key)}
            title={collapsed ? it.label : undefined}
            className={`nav-item w-full text-left px-4 ${collapsed ? 'py-3 flex justify-center' : 'py-[9px]'} flex items-center gap-3 ${active === it.key ? 'active' : ''}`}
            aria-current={active === it.key ? 'page' : undefined}
          >
            <span className={`text-[15px] w-5 text-center ${active === it.key ? '' : 'text-bronze'}`} aria-hidden="true">{it.icon}</span>
            {!collapsed && (
              <span>
                <span className="block text-[13.5px] font-medium leading-tight">{it.label}</span>
                <span className="nav-sub block text-[11px] text-muted leading-tight mt-0.5">{it.sub}</span>
              </span>
            )}
          </button>
        ))}
      </nav>

      <div className="border-t border-line px-4 py-3.5">
        {!collapsed ? (
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-moss text-surface flex items-center justify-center text-[13px] font-semibold shrink-0" aria-hidden="true">SJ</div>
            <div className="min-w-0">
              <div className="text-[13px] font-semibold truncate">Sajid Jamal</div>
              <div className="text-[11px] text-muted truncate">Computer Science Student</div>
            </div>
          </div>
        ) : (
          <div className="w-8 h-8 rounded-full bg-moss text-surface flex items-center justify-center text-[13px] font-semibold mx-auto" title="Sajid Jamal">SJ</div>
        )}
      </div>
    </aside>
  );
}
