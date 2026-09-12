import React, { useCallback, useEffect, useState } from 'react';
import Sidebar, { NavKey } from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Datasets from './pages/Datasets';
import Quality from './pages/Quality';
import Explore from './pages/Explore';
import Visualize from './pages/Visualize';
import Statistics from './pages/Statistics';
import Insights from './pages/Insights';
import ML from './pages/ML';
import Ask from './pages/Ask';
import Reports from './pages/Reports';
import Settings from './pages/Settings';
import { api } from './lib/api';

export default function App() {
  const [nav, setNav] = useState<NavKey>('dashboard');
  const [hasData, setHasData] = useState(false);
  const [filename, setFilename] = useState('');
  const [refreshToken, setRefreshToken] = useState(0);
  const [backendDown, setBackendDown] = useState(false);
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('orion_compact') === '1');

  const refresh = useCallback(async () => {
    try {
      const h = await api.health();
      setBackendDown(false);
      setHasData(h.has_data);
      if (h.has_data) {
        try {
          const s = await api.summary();
          setFilename((s.summary as Record<string, string>).filename || '');
        } catch { /* summary may fail transiently */ }
      } else setFilename('');
    } catch {
      setBackendDown(true);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh, refreshToken]);

  useEffect(() => {
    const onStorage = () => setCollapsed(localStorage.getItem('orion_compact') === '1');
    window.addEventListener('storage', onStorage);
    const t = setInterval(() => setCollapsed(localStorage.getItem('orion_compact') === '1'), 1000);
    return () => { window.removeEventListener('storage', onStorage); clearInterval(t); };
  }, []);

  const bump = () => setRefreshToken((t) => t + 1);

  return (
    <div className="h-full flex">
      <Sidebar
        active={nav}
        onNav={(k) => { setNav(k); }}
        hasData={hasData}
        filename={filename}
        collapsed={collapsed}
      />
      <div className="flex-1 flex flex-col min-w-0 h-full">
        <header className="bg-surface border-b border-line px-5 py-2.5 flex items-center gap-3 shrink-0">
          <button
            onClick={() => { const v = !collapsed; setCollapsed(v); localStorage.setItem('orion_compact', v ? '1' : '0'); }}
            className="btn-ghost w-8 h-8 text-[15px]"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? '→' : '←'}
          </button>
          <div className="text-[12.5px] text-muted">
            {hasData ? <>Working on <b className="text-ink">{filename}</b></> : <>No dataset loaded</>}
          </div>
          <div className="ml-auto flex items-center gap-2">
            <span className={`text-[11.5px] font-medium px-2.5 py-1 rounded-full border ${backendDown ? 'bg-[#F7E9E5] text-[#8C3B2E] border-[#D9A79B]' : 'bg-[#EFF2EA] text-mossdark border-[#B9C2AB]'}`}>
              {backendDown ? '● backend offline' : '● local engine ready'}
            </span>
            {nav !== 'datasets' && (
              <button onClick={() => setNav('datasets')} className="btn-primary px-3.5 py-1.5 text-[12.5px]">
                {hasData ? 'Switch dataset' : 'Import dataset'}
              </button>
            )}
          </div>
        </header>

        {backendDown && (
          <div className="bg-[#F7E9E5] border-b border-[#D9A79B] px-5 py-2.5 text-[13px] text-[#8C3B2E]">
            <b>Backend not reachable.</b> Start it with <code className="font-mono bg-white/70 px-1.5 py-0.5 rounded">cd orion/backend &amp;&amp; uvicorn app:app --port 8000</code> then refresh.
          </div>
        )}

        <main className="flex-1 overflow-y-auto px-5 md:px-7 py-5 max-w-[1240px] w-full mx-auto">
          {nav === 'dashboard' && <Dashboard onNav={setNav} refreshToken={refreshToken} onImported={bump} />}
          {nav === 'datasets' && <Datasets onImported={() => { bump(); refresh(); }} refreshToken={refreshToken} />}
          {nav === 'quality' && <Quality onChanged={bump} refreshToken={refreshToken} />}
          {nav === 'explore' && <Explore refreshToken={refreshToken} />}
          {nav === 'visualize' && <Visualize refreshToken={refreshToken} />}
          {nav === 'statistics' && <Statistics refreshToken={refreshToken} />}
          {nav === 'insights' && <Insights refreshToken={refreshToken} />}
          {nav === 'ml' && <ML refreshToken={refreshToken} />}
          {nav === 'ask' && <Ask refreshToken={refreshToken} />}
          {nav === 'reports' && <Reports refreshToken={refreshToken} />}
          {nav === 'settings' && <Settings />}
        </main>

        <footer className="shrink-0 border-t border-line bg-surface px-5 py-2 text-[11px] text-muted flex items-center gap-2">
          <span><b className="text-ink">ORION</b> · Turn Data Into Decisions.</span>
          <span className="ml-auto">Local-first · no database · no API keys · datasets never leave this computer</span>
        </footer>
      </div>
    </div>
  );
}
