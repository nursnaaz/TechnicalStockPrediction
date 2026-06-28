import { useState, useMemo } from "react";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";
import FormField from "@cloudscape-design/components/form-field";
import Input from "@cloudscape-design/components/input";
import Button from "@cloudscape-design/components/button";
import Table from "@cloudscape-design/components/table";
import Box from "@cloudscape-design/components/box";
import StatusIndicator from "@cloudscape-design/components/status-indicator";
import ColumnLayout from "@cloudscape-design/components/column-layout";
import Slider from "@cloudscape-design/components/slider";
import DatePicker from "@cloudscape-design/components/date-picker";
import Select from "@cloudscape-design/components/select";
import Tabs from "@cloudscape-design/components/tabs";
import Badge from "@cloudscape-design/components/badge";
import ProgressBar from "@cloudscape-design/components/progress-bar";

import { executeBacktest } from "../services/backtestApi";
import type { BacktestResponse, TradeResult } from "../types/backtest";

// Halal stock presets
const PRESETS = {
  "Top 20": "AAPL,MSFT,NVDA,GOOGL,TSLA,AVGO,LLY,JNJ,UNH,HD,COST,PFE,ABBV,TMO,ORCL,ADBE,CRM,NKE,CSCO,PG",
  "Top 50": "AAPL,MSFT,NVDA,GOOGL,TSLA,AVGO,LLY,JNJ,UNH,PFE,ABBV,TMO,ABT,DHR,MRK,HD,COST,TGT,NKE,PG,KO,PEP,WMT,ORCL,ADBE,CRM,CSCO,AMD,QCOM,TXN,AMAT,BA,CAT,DE,UPS,HON,XOM,CVX,COP,LIN,APD,V,MA,PYPL,DDOG,CRWD,PANW,NOW,TSM,IBM",
  "Tech": "AAPL,MSFT,NVDA,GOOGL,AVGO,ORCL,ADBE,CRM,CSCO,AMD,QCOM,TXN,AMAT,LRCX,KLAC,MRVL,NXPI,ADI,TSM,IBM,DDOG,CRWD,PANW,NET,NOW",
  "Healthcare": "LLY,JNJ,UNH,PFE,ABBV,TMO,ABT,DHR,MRK,BMY,AMGN,GILD,REGN,VRTX,ISRG",
  "Consumer": "TSLA,HD,COST,TGT,NKE,SBUX,MCD,CMG,LULU,BKNG,PG,KO,PEP,WMT,CL",
  "Energy": "XOM,CVX,COP,SLB,EOG,PSX,MPC,VLO,OXY,HAL",
  "Fintech": "V,MA,PYPL,FIS,FISV,SHOP,UBER",
};

/** Recompute confusion matrix from raw trades using given thresholds */
function computeConfusionMatrix(
  trades: TradeResult[], scoreThreshold: number, gainThreshold: number
) {
  let tp = 0, fp = 0, fn = 0, tn = 0;
  for (const t of trades) {
    if (t.status !== "analyzed" || t.max_gain_pct === null) continue;
    const predictedBullish = t.score >= scoreThreshold;
    const actuallyWentUp = t.max_gain_pct >= gainThreshold;
    if (predictedBullish && actuallyWentUp) tp++;
    else if (predictedBullish && !actuallyWentUp) fp++;
    else if (!predictedBullish && actuallyWentUp) fn++;
    else tn++;
  }
  const total = tp + fp + fn + tn;
  const accuracy = total > 0 ? (tp + tn) / total : 0;
  const precision = (tp + fp) > 0 ? tp / (tp + fp) : 0;
  const recall = (tp + fn) > 0 ? tp / (tp + fn) : 0;
  const f1 = (precision + recall) > 0 ? (2 * precision * recall) / (precision + recall) : 0;
  return { tp, fp, fn, tn, total, accuracy, precision, recall, f1 };
}

function classifyTrade(trade: TradeResult, scoreThreshold: number, gainThreshold: number): string {
  if (trade.status !== "analyzed" || trade.max_gain_pct === null) return "—";
  const predicted = trade.score >= scoreThreshold;
  const actual = trade.max_gain_pct >= gainThreshold;
  if (predicted && actual) return "true_positive";
  if (predicted && !actual) return "false_positive";
  if (!predicted && actual) return "false_negative";
  return "true_negative";
}

/** Generate HTML report for download */
function generateReport(result: BacktestResponse, cm: ReturnType<typeof computeConfusionMatrix>, scoreThreshold: number, gainThreshold: number): string {
  const trades = result.trades ?? [];
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Backtest Report - ${result.as_of_date}</title>
<style>body{font-family:system-ui,-apple-system,sans-serif;max-width:1200px;margin:0 auto;padding:20px;background:#f9fafb}
h1{color:#0972d3}table{border-collapse:collapse;width:100%;margin:16px 0}th,td{border:1px solid #ddd;padding:8px;text-align:left}
th{background:#0972d3;color:white}.tp{background:#d4edda}.fp{background:#f8d7da}.fn{background:#fff3cd}.tn{background:#e2e8f0}
.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:20px 0}
.metric-card{background:white;border-radius:8px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,0.1);text-align:center}
.metric-value{font-size:2em;font-weight:bold;color:#0972d3}.metric-label{color:#666;font-size:0.9em}</style></head>
<body><h1>Backtest Report</h1>
<p><strong>Date:</strong> ${result.as_of_date} | <strong>Horizon:</strong> ${result.horizon_days} days | <strong>Market:</strong> ${result.market_regime} | <strong>Trades:</strong> ${result.trades_analyzed}</p>
<p><strong>Thresholds:</strong> Score ≥ ${scoreThreshold} | Gain ≥ ${gainThreshold}%</p>
<div class="metric-grid">
<div class="metric-card"><div class="metric-value">${(cm.accuracy*100).toFixed(0)}%</div><div class="metric-label">Accuracy</div></div>
<div class="metric-card"><div class="metric-value">${(cm.precision*100).toFixed(0)}%</div><div class="metric-label">Precision</div></div>
<div class="metric-card"><div class="metric-value">${(cm.recall*100).toFixed(0)}%</div><div class="metric-label">Recall</div></div>
<div class="metric-card"><div class="metric-value">${(cm.f1*100).toFixed(0)}%</div><div class="metric-label">F1 Score</div></div>
</div>
<h2>Confusion Matrix</h2>
<table><tr><th></th><th>Actually ≥${gainThreshold}%</th><th>Actually &lt;${gainThreshold}%</th></tr>
<tr><td><strong>Predicted Bullish (≥${scoreThreshold})</strong></td><td class="tp">TP: ${cm.tp}</td><td class="fp">FP: ${cm.fp}</td></tr>
<tr><td><strong>Not Predicted (&lt;${scoreThreshold})</strong></td><td class="fn">FN: ${cm.fn}</td><td class="tn">TN: ${cm.tn}</td></tr></table>
<h2>Trade Details</h2><table><tr><th>Ticker</th><th>Score</th><th>Entry</th><th>Max Price</th><th>Max Gain</th><th>Return</th><th>Classification</th></tr>
${trades.map(t => {const cls = classifyTrade(t, scoreThreshold, gainThreshold); return `<tr class="${cls}"><td>${t.ticker}</td><td>${t.score}</td><td>$${t.entry_price.toFixed(2)}</td><td>$${(t.max_price??0).toFixed(2)}</td><td>${(t.max_gain_pct??0).toFixed(1)}%</td><td>${(t.return_pct??0).toFixed(1)}%</td><td>${cls.replace('_',' ').toUpperCase()}</td></tr>`;}).join('')}
</table><p><em>Generated ${new Date().toISOString()}</em></p></body></html>`;
}


export default function BacktestPanel() {
  const [asOfDate, setAsOfDate] = useState("");
  const [tickers, setTickers] = useState("");
  const [horizonDays, setHorizonDays] = useState("30");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedPreset, setSelectedPreset] = useState<{label:string,value:string}|null>(null);

  // Dynamic thresholds
  const [scoreThreshold, setScoreThreshold] = useState(50);
  const [gainThreshold, setGainThreshold] = useState(5);
  const [sortingColumn, setSortingColumn] = useState<{sortingField:string}|undefined>(undefined);
  const [sortingDescending, setSortingDescending] = useState(false);

  const handlePresetChange = (option: {label?:string,value?:string}) => {
    if (option.value && option.value in PRESETS) {
      setTickers(PRESETS[option.value as keyof typeof PRESETS]);
      setSelectedPreset({label: option.label ?? "", value: option.value});
    }
  };

  const handleBacktest = async () => {
    if (!asOfDate.trim()) { setError("Please select a date"); return; }
    if (!tickers.trim()) { setError("Please enter tickers or select a preset"); return; }
    setLoading(true); setError(null); setResult(null);
    try {
      const tickerList = tickers.split(/[,\s]+/).map(t => t.trim().toUpperCase()).filter(t => t.length > 0);
      const data = await executeBacktest({
        as_of_date: asOfDate.trim(), tickers: tickerList, horizon_days: parseInt(horizonDays) || 30,
      });
      setResult(data);
    } catch (e) { setError(e instanceof Error ? e.message : "Backtest failed"); }
    finally { setLoading(false); }
  };

  const handleDownloadReport = () => {
    if (!result) return;
    const html = generateReport(result, cm, scoreThreshold, gainThreshold);
    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `backtest-report-${result.as_of_date}.html`;
    a.click(); URL.revokeObjectURL(url);
  };

  const trades = result?.trades ?? [];

  const sortedTrades = useMemo(() => {
    if (!sortingColumn?.sortingField) return trades;
    const field = sortingColumn.sortingField as keyof TradeResult;
    const sorted = [...trades].sort((a, b) => {
      const aVal = a[field]; const bVal = b[field];
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;
      if (typeof aVal === "string" && typeof bVal === "string") return aVal.localeCompare(bVal);
      if (typeof aVal === "number" && typeof bVal === "number") return aVal - bVal;
      return 0;
    });
    return sortingDescending ? sorted.reverse() : sorted;
  }, [trades, sortingColumn, sortingDescending]);

  const cm = useMemo(
    () => computeConfusionMatrix(trades, scoreThreshold, gainThreshold),
    [trades, scoreThreshold, gainThreshold]
  );

  // Score distribution for visualization
  const scoreDistribution = useMemo(() => {
    const buckets = [
      { label: "0-29", min: 0, max: 29, count: 0, color: "#d13212" },
      { label: "30-49", min: 30, max: 49, count: 0, color: "#ff9900" },
      { label: "50-64", min: 50, max: 64, count: 0, color: "#f2c94c" },
      { label: "65-79", min: 65, max: 79, count: 0, color: "#67c23a" },
      { label: "80-100", min: 80, max: 100, count: 0, color: "#0972d3" },
    ];
    for (const t of trades) {
      for (const b of buckets) {
        if (t.score >= b.min && t.score <= b.max) { b.count++; break; }
      }
    }
    return buckets;
  }, [trades]);

  const columnDefinitions = useMemo(() => [
    { id: "ticker", header: "Ticker", cell: (item: TradeResult) => <Box fontWeight="bold">{item.ticker}</Box>, sortingField: "ticker", width: 80 },
    { id: "score", header: "Score", cell: (item: TradeResult) => (
      <Box color={item.score >= scoreThreshold ? "text-status-success" : "text-status-inactive"}>
        {item.score}{item.score >= scoreThreshold ? " ★" : ""}
      </Box>), sortingField: "score", width: 90 },
    { id: "entry_price", header: "Entry", cell: (item: TradeResult) => `$${item.entry_price.toFixed(2)}`, sortingField: "entry_price", width: 90 },
    { id: "max_price", header: "Max Price", cell: (item: TradeResult) => item.max_price ? `$${item.max_price.toFixed(2)}` : "—", sortingField: "max_price", width: 100 },
    { id: "max_gain_pct", header: "Max Gain", cell: (item: TradeResult) => (
      <Box color={(item.max_gain_pct ?? 0) >= gainThreshold ? "text-status-success" : "text-status-inactive"}>
        {item.max_gain_pct !== null ? `${item.max_gain_pct.toFixed(1)}%` : "—"}
      </Box>), sortingField: "max_gain_pct", width: 95 },
    { id: "return_pct", header: "Return", cell: (item: TradeResult) => (
      <Box color={(item.return_pct ?? 0) > 0 ? "text-status-success" : "text-status-error"}>
        {item.return_pct !== null ? `${item.return_pct.toFixed(1)}%` : "—"}
      </Box>), sortingField: "return_pct", width: 85 },
    { id: "classification", header: "Class", cell: (item: TradeResult) => {
      const cls = classifyTrade(item, scoreThreshold, gainThreshold);
      if (cls === "true_positive") return <Badge color="green">TP</Badge>;
      if (cls === "true_negative") return <Badge color="blue">TN</Badge>;
      if (cls === "false_positive") return <Badge color="red">FP</Badge>;
      if (cls === "false_negative") return <Badge color="grey">FN</Badge>;
      return "—";
    }, sortingField: "classification", width: 70 },
  ], [scoreThreshold, gainThreshold]);

  return (
    <SpaceBetween size="l">
      {/* Input Form with Presets */}
      <Container header={<Header variant="h2" description="Point-in-time backtesting with zero look-ahead bias">Backtest Scanner</Header>}>
        <SpaceBetween size="m">
          <ColumnLayout columns={4}>
            <FormField label="As-of Date" description="Only data up to this date is used">
              <DatePicker value={asOfDate} onChange={({ detail }) => setAsOfDate(detail.value)} placeholder="YYYY-MM-DD" disabled={loading} />
            </FormField>
            <FormField label="Halal Preset" description="Quick-fill ticker list">
              <Select
                selectedOption={selectedPreset}
                onChange={({ detail }) => handlePresetChange(detail.selectedOption)}
                options={Object.keys(PRESETS).map(k => ({ label: k, value: k }))}
                placeholder="Choose preset..."
              />
            </FormField>
            <FormField label="Horizon (days)">
              <Input value={horizonDays} onChange={({ detail }) => setHorizonDays(detail.value)} type="number" disabled={loading} />
            </FormField>
            <FormField label="Action">
              <SpaceBetween size="xs" direction="horizontal">
                <Button variant="primary" onClick={handleBacktest} loading={loading} iconName="search">Run</Button>
                {result && <Button onClick={handleDownloadReport} iconName="download">Report</Button>}
              </SpaceBetween>
            </FormField>
          </ColumnLayout>
          <FormField label="Tickers" description="Comma-separated symbols (or use preset above)">
            <Input value={tickers} onChange={({ detail }) => setTickers(detail.value)} placeholder="AAPL, MSFT, NVDA..." disabled={loading} />
          </FormField>
        </SpaceBetween>
      </Container>

      {error && <Container><StatusIndicator type="error">{error}</StatusIndicator></Container>}

      {loading && (
        <Container><ProgressBar value={50} label="Running backtest..." description="Fetching historical data and computing scores..." /></Container>
      )}

      {/* Results Section */}
      {trades.length > 0 && (
        <Tabs tabs={[
          { label: "Dashboard", id: "dashboard", content: (
            <SpaceBetween size="l">
              {/* Sliders */}
              <Container header={<Header variant="h3">Threshold Tuning</Header>}>
                <ColumnLayout columns={2}>
                  <FormField label={`Score Threshold: ${scoreThreshold}`}
                    constraintText="↑ Higher = stricter predictions | ↓ Lower = catch more">
                    <span data-testid="score-threshold-slider">
                      <Slider value={scoreThreshold} onChange={({ detail }) => setScoreThreshold(detail.value)} min={10} max={100} step={5} />
                    </span>
                  </FormField>
                  <FormField label={`Gain Threshold: ${gainThreshold}%`}
                    constraintText="↑ Higher = harder bar for 'bullish' | ↓ Lower = easier">
                    <span data-testid="gain-threshold-slider">
                      <Slider value={gainThreshold} onChange={({ detail }) => setGainThreshold(detail.value)} min={1} max={25} step={1} />
                    </span>
                  </FormField>
                </ColumnLayout>
              </Container>

              {/* Key Metrics Cards */}
              <ColumnLayout columns={4} variant="text-grid">
                <Container>
                  <Box variant="awsui-key-label">Accuracy</Box>
                  <Box variant="h1" color={cm.accuracy >= 0.5 ? "text-status-success" : "text-status-error"}>
                    {(cm.accuracy * 100).toFixed(0)}%
                  </Box>
                  <Box variant="small">(TP+TN) / Total = ({cm.tp}+{cm.tn}) / {cm.total}</Box>
                </Container>
                <Container>
                  <Box variant="awsui-key-label">Precision</Box>
                  <Box variant="h1" color={cm.precision >= 0.6 ? "text-status-success" : "text-status-warning"}>
                    <span data-testid="metric-precision">{(cm.precision * 100).toFixed(0)}%</span>
                  </Box>
                  <Box variant="small">When we say bullish, how often right</Box>
                </Container>
                <Container>
                  <Box variant="awsui-key-label">Recall</Box>
                  <Box variant="h1" color={cm.recall >= 0.5 ? "text-status-success" : "text-status-warning"}>
                    <span data-testid="metric-recall">{(cm.recall * 100).toFixed(0)}%</span>
                  </Box>
                  <Box variant="small">Of all gainers, how many we caught</Box>
                </Container>
                <Container>
                  <Box variant="awsui-key-label">F1 Score</Box>
                  <Box variant="h1">{(cm.f1 * 100).toFixed(0)}%</Box>
                  <Box variant="small">Harmonic mean of Prec & Recall</Box>
                </Container>
              </ColumnLayout>

              {/* Confusion Matrix Visual */}
              <Container header={<Header variant="h3">Confusion Matrix</Header>}>
                <div style={{ display: "grid", gridTemplateColumns: "120px 1fr 1fr", gap: "4px", maxWidth: "500px" }}>
                  <div></div>
                  <div style={{ textAlign: "center", fontWeight: "bold", padding: "8px", background: "#f0f0f0" }}>Actual ≥{gainThreshold}%</div>
                  <div style={{ textAlign: "center", fontWeight: "bold", padding: "8px", background: "#f0f0f0" }}>Actual &lt;{gainThreshold}%</div>
                  <div style={{ fontWeight: "bold", padding: "8px", background: "#f0f0f0", display: "flex", alignItems: "center" }}>Predicted ≥{scoreThreshold}</div>
                  <div data-testid="cm-tp" style={{ textAlign: "center", padding: "16px", background: "#d4edda", borderRadius: "4px", fontSize: "1.5em", fontWeight: "bold" }}>{cm.tp}<br/><span style={{fontSize:"0.5em",color:"#155724"}}>TRUE POS</span></div>
                  <div data-testid="cm-fp" style={{ textAlign: "center", padding: "16px", background: "#f8d7da", borderRadius: "4px", fontSize: "1.5em", fontWeight: "bold" }}>{cm.fp}<br/><span style={{fontSize:"0.5em",color:"#721c24"}}>FALSE POS</span></div>
                  <div style={{ fontWeight: "bold", padding: "8px", background: "#f0f0f0", display: "flex", alignItems: "center" }}>Predicted &lt;{scoreThreshold}</div>
                  <div data-testid="cm-fn" style={{ textAlign: "center", padding: "16px", background: "#fff3cd", borderRadius: "4px", fontSize: "1.5em", fontWeight: "bold" }}>{cm.fn}<br/><span style={{fontSize:"0.5em",color:"#856404"}}>FALSE NEG</span></div>
                  <div data-testid="cm-tn" style={{ textAlign: "center", padding: "16px", background: "#e2e8f0", borderRadius: "4px", fontSize: "1.5em", fontWeight: "bold" }}>{cm.tn}<br/><span style={{fontSize:"0.5em",color:"#2d3748"}}>TRUE NEG</span></div>
                </div>
              </Container>

              {/* Score Distribution Chart */}
              <Container header={<Header variant="h3">Score Distribution</Header>}>
                <div style={{ display: "flex", alignItems: "flex-end", gap: "8px", height: "120px", padding: "0 20px" }}>
                  {scoreDistribution.map((bucket) => {
                    const maxCount = Math.max(...scoreDistribution.map(b => b.count), 1);
                    const height = (bucket.count / maxCount) * 100;
                    return (
                      <div key={bucket.label} style={{ flex: 1, textAlign: "center" }}>
                        <div style={{ fontSize: "0.75em", marginBottom: "4px" }}>{bucket.count}</div>
                        <div style={{
                          height: `${height}%`, minHeight: bucket.count > 0 ? "4px" : "0",
                          background: bucket.min >= scoreThreshold ? bucket.color : "#ccc",
                          borderRadius: "4px 4px 0 0", transition: "all 0.3s"
                        }} />
                        <div style={{ fontSize: "0.7em", marginTop: "4px", color: "#666" }}>{bucket.label}</div>
                      </div>
                    );
                  })}
                </div>
                <Box variant="small" textAlign="center" margin={{ top: "xs" }}>
                  Colored bars = predicted bullish (score ≥{scoreThreshold}) | Grey = not predicted
                </Box>
              </Container>

              {/* Summary Info */}
              <ColumnLayout columns={3} variant="text-grid">
                <Container>
                  <Box variant="awsui-key-label">Market Regime</Box>
                  <Box variant="h2">{result?.market_regime ?? "—"}</Box>
                </Container>
                <Container>
                  <Box variant="awsui-key-label">Avg Return (all trades)</Box>
                  <Box variant="h2" color={(result?.metrics?.avg_return ?? 0) >= 0 ? "text-status-success" : "text-status-error"}>
                    {(result?.metrics?.avg_return ?? 0).toFixed(1)}%
                  </Box>
                </Container>
                <Container>
                  <Box variant="awsui-key-label">Trades Analyzed</Box>
                  <Box variant="h2">{cm.total} / {result?.total_candidates ?? 0}</Box>
                </Container>
              </ColumnLayout>
            </SpaceBetween>
          )},
          { label: "Trade Details", id: "trades", content: (
            <Table
              key={`${scoreThreshold}-${gainThreshold}`}
              header={<Header variant="h3" counter={`(${trades.length})`} actions={
                <Button onClick={handleDownloadReport} iconName="download" variant="normal">Download Report</Button>
              }>Trade-by-Trade Results</Header>}
              columnDefinitions={columnDefinitions}
              items={sortedTrades}
              sortingColumn={sortingColumn}
              sortingDescending={sortingDescending}
              onSortingChange={({ detail }) => {
                setSortingColumn(detail.sortingColumn as {sortingField:string});
                setSortingDescending(detail.isDescending ?? false);
              }}
              variant="container"
              wrapLines
            />
          )},
        ]} />
      )}

      {/* Ran, but the V3 engine produced no trades (e.g. bearish market → 0 BUYs) */}
      {result && !loading && trades.length === 0 && (
        <Container data-testid="backtest-empty">
          <Box textAlign="center" color="inherit">
            <b>No trades for this scan</b>
            <Box variant="p" color="inherit">
              The V3 engine surfaced no qualifying candidates for this date
              {result.market_regime === "bearish" ? " — the market was bearish (zero buy signals)." : "."}
            </Box>
          </Box>
        </Container>
      )}
    </SpaceBetween>
  );
}
