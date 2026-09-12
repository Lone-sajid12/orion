import React, { useEffect, useRef } from 'react';

// Plotly is loaded as a local static script (public/plotly.min.js) so the
// production bundler never has to parse the 4.5MB library. Fully offline.
// Minimal structural typing for the small API surface ORION uses.
type PlotlyDatum = Record<string, unknown>;
type PlotlyLayout = Record<string, unknown>;
interface PlotlyStatic {
  react(el: HTMLElement, data: PlotlyDatum[], layout: PlotlyLayout, config?: Record<string, unknown>): void;
  purge(el: HTMLElement): void;
  Plots: { resize(el: HTMLElement): void };
}
function getPlotly(): PlotlyStatic | null {
  return (window as unknown as { Plotly?: PlotlyStatic }).Plotly ?? null;
}

const BASE_LAYOUT = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { family: 'Inter, sans-serif', size: 12, color: '#252522' },
  margin: { l: 52, r: 16, t: 12, b: 48 },
  xaxis: { gridcolor: '#E7E2D5', zerolinecolor: '#D9D4C8' },
  yaxis: { gridcolor: '#E7E2D5', zerolinecolor: '#D9D4C8' },
  showlegend: true,
  legend: { orientation: 'h', y: -0.22, font: { size: 11 } },
};

const PALETTE = ['#66745A', '#A68A64', '#252522', '#8A9B7C', '#C2A878', '#5A6B8A', '#8A6B5A', '#4C5744'];

export function PlotView({ chart, height = 380 }: { chart: Record<string, unknown>; height?: number }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const el = ref.current;
    const Plotly = getPlotly();
    if (!Plotly) {
      // Script still loading (slow disk): retry shortly, then show a message.
      const timer = setTimeout(() => {
        if (el && !getPlotly()) {
          el.innerHTML = '<div style="padding:24px;color:#68665E;font-size:13px">Chart library is still loading… please wait a moment and rebuild the chart.</div>';
        }
      }, 2500);
      return () => clearTimeout(timer);
    }
    let data: PlotlyDatum[] = [];
    let layout: Record<string, unknown> = { ...BASE_LAYOUT, height };
    const t = chart.type as string;

    try {
      if (t === 'histogram') {
        const counts = chart.counts as number[];
        const edges = chart.edges as number[];
        const centers = edges.slice(0, -1).map((e, i) => (e + edges[i + 1]) / 2);
        data = [{ x: centers, y: counts, type: 'bar', marker: { color: '#66745A' }, name: chart.x as string, hovertemplate: '%{y} obs<extra></extra>' }];
        layout = { ...layout, xaxis: { ...BASE_LAYOUT.xaxis, title: { text: chart.x as string } }, yaxis: { ...BASE_LAYOUT.yaxis, title: { text: 'Count' } } };
      } else if (t === 'box') {
        const series = chart.series as { name: string; values: number[] }[];
        data = series.map((s, i) => ({
          y: s.values, type: 'box', name: s.name,
          marker: { color: PALETTE[i % PALETTE.length] },
          boxpoints: series.length > 1 ? false : ('outliers' as const),
        }));
        layout = { ...layout, yaxis: { ...BASE_LAYOUT.yaxis, title: { text: (chart.y as string) || 'Value' } } };
      } else if (t === 'scatter') {
        const x = chart.x as number[]; const y = chart.y as number[];
        if (chart.color) {
          const cats = chart.color as string[];
          const uniq = [...new Set(cats)].slice(0, 8);
          data = uniq.map((c, i) => {
            const xs: number[] = []; const ys: number[] = [];
            cats.forEach((cc, k) => { if (cc === c) { xs.push(x[k]); ys.push(y[k]); } });
            return { x: xs, y: ys, mode: 'markers', type: 'scatter', name: c, marker: { color: PALETTE[i % PALETTE.length], size: 6, opacity: 0.7 } };
          });
        } else {
          data = [{ x, y, mode: 'markers', type: 'scatter', name: 'observations', marker: { color: '#66745A', size: 6, opacity: 0.6 } }];
        }
        layout = { ...layout, xaxis: { ...BASE_LAYOUT.xaxis, title: { text: chart.x as string } }, yaxis: { ...BASE_LAYOUT.yaxis, title: { text: chart.y as string } } };
      } else if (t === 'bar' || t === 'line' || t === 'area') {
        const series = chart.series as { name: string; x: string[]; y: (number | null)[] }[];
        data = series.map((s, i) => {
          const color = PALETTE[i % PALETTE.length];
          if (t === 'bar') return { x: s.x, y: s.y, type: 'bar', name: s.name, marker: { color } };
          return {
            x: s.x, y: s.y, type: 'scatter', mode: 'lines+markers', name: s.name,
            line: { color, width: 2.2 }, marker: { color, size: 5 },
            fill: t === 'area' ? 'tozeroy' : undefined,
            fillcolor: t === 'area' ? color + '33' : undefined,
          };
        });
        layout = { ...layout, yaxis: { ...BASE_LAYOUT.yaxis, title: { text: (chart.ylabel as string) || '' } } };
        if (t === 'bar' && series.length > 1) layout = { ...layout, barmode: 'group' };
      } else if (t === 'pie' || t === 'donut') {
        data = [{
          labels: chart.labels as string[], values: chart.values as number[], type: 'pie',
          hole: t === 'donut' ? 0.5 : 0, marker: { colors: PALETTE },
          textinfo: 'label+percent', textfont: { size: 11 },
        }];
        layout = { ...layout, margin: { l: 16, r: 16, t: 12, b: 12 } };
      } else if (t === 'heatmap' || chart.matrix) {
        const cols = chart.columns as string[];
        const mat = chart.matrix as (number | null)[][];
        data = [{
          z: mat, x: cols, y: cols, type: 'heatmap',
          colorscale: [[0, '#8C3B2E'], [0.5, '#F3EFE6'], [1, '#4C5744']],
          zmin: -1, zmax: 1, hovertemplate: '%{x} ↔ %{y}: %{z}<extra></extra>',
          colorbar: { thickness: 12 },
        } as unknown as PlotlyDatum];
        layout = { ...layout, height: Math.max(380, cols.length * 34 + 120), margin: { l: 110, r: 16, t: 12, b: 110 } };
      }
      Plotly.react(el, data, layout, { responsive: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d', 'select2d'] });
    } catch (e) {
      console.error('plot error', e);
    }
    const onResize = () => { try { Plotly.Plots.resize(el); } catch { /* noop */ } };
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      try { Plotly.purge(el); } catch { /* noop */ }
    };
  }, [chart, height]);

  return <div ref={ref} style={{ width: '100%', height }} role="img" aria-label="Data chart" />;
}

export function UnivPlots({ data }: { data: { plots: Record<string, unknown>; column: string } }) {
  const plots = data.plots;
  if (plots.histogram) {
    const h = plots.histogram as { counts: number[]; edges: number[] };
    return <PlotView chart={{ type: 'histogram', counts: h.counts, edges: h.edges, x: data.column }} height={320} />;
  }
  if (plots.bars) {
    const bars = plots.bars as { value: string; count: number }[];
    const chart = {
      type: 'bar',
      series: [{ name: 'count', x: bars.map((b) => b.value), y: bars.map((b) => b.count) }],
      ylabel: 'Count',
    };
    return <PlotView chart={chart} height={320} />;
  }
  return null;
}
