// Builds a self-contained, downloadable HTML report of a Live Scanner result.

import type { ScanResponse, TickerScore } from "../types/scan";

const BREAKDOWN_KEYS: [string, string][] = [
  ["trend", "Trend"],
  ["momentum", "Momentum"],
  ["strength", "Strength"],
  ["confirmation", "Confirmation"],
  ["stage_pattern", "Stage+Pattern"],
  ["extension_penalty", "Extension"],
  ["climax_penalty", "Climax"],
  ["divergence_penalty", "Divergence"],
];

function activeSignals(t: TickerScore): string {
  const s = t.signals;
  const on: string[] = [];
  if (s.price_above_sma50) on.push("SMA50");
  if (s.price_above_ema20) on.push("EMA20");
  if (s.macd_above_signal) on.push("MACD");
  if (s.macd_histogram_positive) on.push("MACD+");
  if (s.volume_above_average) on.push("Vol");
  if (s.relative_strength_positive) on.push("RS");
  return on.join(", ") || "—";
}

function statusLabel(t: TickerScore): string {
  if (t.is_candidate) return "Candidate";
  if (t.passed_hard_filters) return "Below threshold";
  if (t.passed_hard_filters === false) return "Failed filters";
  return "—";
}

/** Generate the full HTML report string for a scan result. */
export function buildScanReportHtml(results: ScanResponse): string {
  const rows = results.ranked_tickers;
  const avg =
    rows.length > 0 ? Math.round(rows.reduce((a, t) => a + t.bullish_score, 0) / rows.length) : 0;
  const hasStatus = rows.some((t) => t.passed_hard_filters != null || t.is_candidate != null);

  const css = `
    body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f5f7fa;color:#1a2b3c}
    .wrap{max-width:1200px;margin:0 auto;padding:28px}
    h1{color:#0b3d66;margin-bottom:4px}.sub{color:#5b6b7b;margin-top:0}
    .kpis{display:flex;gap:14px;flex-wrap:wrap;margin:16px 0}
    .kpi{background:#fff;border-radius:10px;padding:14px 20px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
    .kpi .v{font-size:24px;font-weight:700;color:#0b3d66}.kpi .l{color:#5b6b7b;font-size:12px}
    table{border-collapse:collapse;width:100%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.08);font-size:13px}
    th,td{padding:7px 9px;border:1px solid #e6ebf1;text-align:center}
    th{background:#0b5394;color:#fff}td.l{text-align:left}
    .pos{color:#137333;font-weight:600}.neg{color:#a50e0e;font-weight:600}
    .badge{display:inline-block;padding:1px 8px;border-radius:10px;color:#fff;font-size:11px;font-weight:600}`;

  const regimeColor =
    results.market_regime === "bullish" ? "#137333" : results.market_regime === "bearish" ? "#a50e0e" : "#856404";

  const bdHeaders = BREAKDOWN_KEYS.map(([, label]) => `<th>${label}</th>`).join("");
  const body = rows
    .map((t, i) => {
      const bdCells = BREAKDOWN_KEYS.map(([k]) => {
        const v = t.score_breakdown?.[k];
        if (v === undefined) return "<td>—</td>";
        const cls = v < 0 ? "neg" : v > 0 ? "pos" : "";
        return `<td class="${cls}">${v > 0 ? "+" + v : v}</td>`;
      }).join("");
      return `<tr>
        <td>${i + 1}</td><td class="l"><b>${t.ticker}</b></td>
        <td><span class="badge" style="background:${t.bullish_score >= 70 ? "#137333" : t.bullish_score >= 40 ? "#0972d3" : "#7d8998"}">${t.bullish_score}</span></td>
        ${hasStatus ? `<td>${statusLabel(t)}</td>` : ""}
        <td>$${t.current_price.toFixed(2)}</td>
        ${bdCells}
        <td class="l">${activeSignals(t)}</td>
      </tr>`;
    })
    .join("");

  return `<!doctype html><html><head><meta charset="utf-8"><title>Scan Report</title><style>${css}</style></head>
<body><div class="wrap">
  <h1>Bullish Stock Scan Report</h1>
  <p class="sub">Generated ${new Date().toLocaleString()} · scan ${results.scan_id}</p>
  <div class="kpis">
    <div class="kpi"><div class="v" style="color:${regimeColor}">${results.market_regime.toUpperCase()}</div><div class="l">Market regime</div></div>
    <div class="kpi"><div class="v">${results.ranked_tickers.length}</div><div class="l">Results</div></div>
    <div class="kpi"><div class="v">${avg}</div><div class="l">Avg bullish score</div></div>
    <div class="kpi"><div class="v">${results.score_threshold ?? "—"}</div><div class="l">BUY threshold</div></div>
  </div>
  <table>
    <tr><th>Rank</th><th>Ticker</th><th>Score</th>${hasStatus ? "<th>Status</th>" : ""}<th>Price</th>${bdHeaders}<th>Active signals</th></tr>
    ${body || `<tr><td colspan="20">No results.</td></tr>`}
  </table>
</div></body></html>`;
}

/** Trigger a browser download of the scan report. */
export function downloadScanReport(results: ScanResponse): void {
  const html = buildScanReportHtml(results);
  const blob = new Blob([html], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const stamp = new Date().toISOString().slice(0, 10);
  a.href = url;
  a.download = `scan-report-${stamp}.html`;
  a.click();
  URL.revokeObjectURL(url);
}
