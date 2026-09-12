export const API = '';

async function handle(res: Response) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.ok === false) {
    throw new Error(data.error || data.detail || `Request failed (${res.status})`);
  }
  return data;
}

export const api = {
  async health() {
    return handle(await fetch('/api/health'));
  },
  async upload(file: File) {
    const fd = new FormData();
    fd.append('file', file);
    return handle(await fetch('/api/upload', { method: 'POST', body: fd }));
  },
  async loadSample() {
    return handle(await fetch('/api/load-sample', { method: 'POST' }));
  },
  async summary() {
    return handle(await fetch('/api/dataset/summary'));
  },
  async preview(page = 1, page_size = 25, search = '', sort_col = '', sort_dir = 'asc') {
    const q = new URLSearchParams({ page: String(page), page_size: String(page_size), search, sort_col, sort_dir });
    return handle(await fetch(`/api/dataset/preview?${q}`));
  },
  async profile() {
    return handle(await fetch('/api/dataset/profile'));
  },
  async column(name: string) {
    return handle(await fetch(`/api/dataset/column?name=${encodeURIComponent(name)}`));
  },
  async columns() {
    return handle(await fetch('/api/dataset/columns'));
  },
  async quality() {
    return handle(await fetch('/api/quality'));
  },
  async cleanApply(op: Record<string, unknown>) {
    return handle(await fetch('/api/clean/apply', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(op),
    }));
  },
  async cleanUndo() {
    return handle(await fetch('/api/clean/undo', { method: 'POST' }));
  },
  async cleanReset() {
    return handle(await fetch('/api/clean/reset', { method: 'POST' }));
  },
  async univariate(col: string) {
    return handle(await fetch(`/api/eda/univariate?col=${encodeURIComponent(col)}`));
  },
  async corrMatrix(method = 'pearson') {
    return handle(await fetch(`/api/eda/correlation?method=${method}`));
  },
  async chart(spec: Record<string, unknown>) {
    return handle(await fetch('/api/eda/chart', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(spec),
    }));
  },
  async bivariate(x: string, y: string) {
    return handle(await fetch(`/api/eda/bivariate?x=${encodeURIComponent(x)}&y=${encodeURIComponent(y)}`));
  },
  async insights() {
    return handle(await fetch('/api/insights'));
  },
  async statsDescriptive(columns?: string[]) {
    return handle(await fetch('/api/stats/descriptive', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ columns }),
    }));
  },
  async statsCorr(x: string, y: string, method = 'pearson') {
    return handle(await fetch('/api/stats/correlation', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ x, y, method }),
    }));
  },
  async statsCI(column: string, level = 0.95) {
    return handle(await fetch('/api/stats/ci', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ column, level }),
    }));
  },
  async statsTTest(numeric: string, group: string, a?: string, b?: string) {
    return handle(await fetch('/api/stats/ttest', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ numeric, group, a, b }),
    }));
  },
  async statsChi2(a: string, b: string) {
    return handle(await fetch('/api/stats/chi2', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ a, b }),
    }));
  },
  async statsAnova(numeric: string, group: string) {
    return handle(await fetch('/api/stats/anova', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ numeric, group }),
    }));
  },
  async mlTargets() {
    return handle(await fetch('/api/ml/targets'));
  },
  async mlTrain(payload: Record<string, unknown>) {
    return handle(await fetch('/api/ml/train', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    }));
  },
  async mlPredict(run_id: string, values: Record<string, unknown>) {
    return handle(await fetch('/api/ml/predict', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ run_id, values }),
    }));
  },
  async ask(question: string) {
    return handle(await fetch('/api/ask', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question }),
    }));
  },
  async aiStatus() {
    return handle(await fetch('/api/ai/status'));
  },
  async aiExplain(prompt: string, model = '') {
    return handle(await fetch('/api/ai/explain', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt, model }),
    }));
  },
  async report() {
    return handle(await fetch('/api/report'));
  },
  reportUrl(format: 'html' | 'markdown') {
    return `/api/report?format=${format}`;
  },
  async codeLog() {
    return handle(await fetch('/api/code-log'));
  },
};

export function fmt(n: unknown): string {
  if (n === null || n === undefined) return '—';
  if (typeof n === 'number') {
    if (!isFinite(n)) return '—';
    if (Number.isInteger(n) && Math.abs(n) >= 1000) return n.toLocaleString('en-IN');
    if (Math.abs(n) >= 1000) return n.toLocaleString('en-IN', { maximumFractionDigits: 2 });
    return String(Math.round(n * 10000) / 10000);
  }
  return String(n);
}
