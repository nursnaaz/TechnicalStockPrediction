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

import { executeBacktest } from "../services/backtestApi";
import type { BacktestResponse, TradeResult } from "../types/backtest";

/** Recompute confusion matrix from raw trades using given thresholds */
function computeConfusionMatrix(
  trades: TradeResult[],
  scoreThreshold: number,
  gainThreshold: number
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

/** Classify a single trade given thresholds */
function classifyTrade(trade: TradeResult, scoreThreshold: number, gainThreshold: number): string {
  if (trade.status !== "analyzed" || trade.max_gain_pct === null) return "—";
  const predicted = trade.score >= scoreThreshold;
  const actual = trade.max_gain_pct >= gainThreshold;
  if (predicted && actual) return "true_positive";
  if (predicted && !actual) return "false_positive";
  if (!predicted && actual) return "false_negative";
  return "true_negative";
}

export default function BacktestPanel() {
  const [asOfDate, setAsOfDate] = useState("");
  const [tickers, setTickers] = useState("");
  const [horizonDays, setHorizonDays] = useState("30");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Dynamic thresholds (sliders) - optimized defaults from backtest analysis
  // Score≥40, Gain≥3% gives best F1=79%, Precision=83%, Recall=75%
  const [scoreThreshold, setScoreThreshold] = useState(40);
  const [gainThreshold, setGainThreshold] = useState(3);
  const [sortingColumn, setSortingColumn] = useState<{ sortingField: string } | undefined>(undefined);
  const [sortingDescending, setSortingDescending] = useState(false);

  const handleBacktest = async () => {
    if (!asOfDate.trim()) {
      setError("Please enter an as-of date (YYYY-MM-DD)");
      return;
    }
    if (!tickers.trim()) {
      setError("Please enter at least one ticker symbol");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const tickerList = tickers
        .split(/[,\s]+/)
        .map((t) => t.trim().toUpperCase())
        .filter((t) => t.length > 0);

      const data = await executeBacktest({
        as_of_date: asOfDate.trim(),
        tickers: tickerList,
        horizon_days: parseInt(horizonDays) || 30,
      });
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Backtest failed");
    } finally {
      setLoading(false);
    }
  };

  const trades = result?.trades ?? [];

  // Sort trades based on current sorting state
  const sortedTrades = useMemo(() => {
    if (!sortingColumn?.sortingField) return trades;
    const field = sortingColumn.sortingField as keyof TradeResult;
    const sorted = [...trades].sort((a, b) => {
      const aVal = a[field];
      const bVal = b[field];
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;
      if (typeof aVal === "string" && typeof bVal === "string") return aVal.localeCompare(bVal);
      if (typeof aVal === "number" && typeof bVal === "number") return aVal - bVal;
      return 0;
    });
    return sortingDescending ? sorted.reverse() : sorted;
  }, [trades, sortingColumn, sortingDescending]);

  // Recompute confusion matrix dynamically based on slider values
  const cm = useMemo(
    () => computeConfusionMatrix(trades, scoreThreshold, gainThreshold),
    [trades, scoreThreshold, gainThreshold]
  );

  // Recompute column definitions when thresholds change so table cells update
  const columnDefinitions = useMemo(() => [
    {
      id: "ticker",
      header: "Ticker",
      cell: (item: TradeResult) => <Box fontWeight="bold">{item.ticker}</Box>,
      sortingField: "ticker",
      width: 80,
    },
    {
      id: "score",
      header: "Bullish Score",
      cell: (item: TradeResult) => (
        <Box color={
          item.score >= scoreThreshold ? "text-status-success" : "text-status-inactive"
        }>
          {item.score}{item.score >= scoreThreshold ? " ★" : ""}
        </Box>
      ),
      sortingField: "score",
      width: 110,
    },
    {
      id: "entry_price",
      header: "Entry Price",
      cell: (item: TradeResult) => `$${item.entry_price.toFixed(2)}`,
      sortingField: "entry_price",
      width: 100,
    },
    {
      id: "max_price",
      header: `Max Price (${result?.horizon_days ?? 30}d)`,
      cell: (item: TradeResult) =>
        item.max_price ? `$${item.max_price.toFixed(2)}` : "—",
      sortingField: "max_price",
      width: 130,
    },
    {
      id: "max_gain_pct",
      header: "Max Gain %",
      cell: (item: TradeResult) => (
        <Box color={
          (item.max_gain_pct ?? 0) >= gainThreshold ? "text-status-success" : "text-status-inactive"
        }>
          {item.max_gain_pct !== null ? `${item.max_gain_pct.toFixed(1)}%` : "—"}
          {(item.max_gain_pct ?? 0) >= gainThreshold ? " ★" : ""}
        </Box>
      ),
      sortingField: "max_gain_pct",
      width: 110,
    },
    {
      id: "classification",
      header: "Classification",
      cell: (item: TradeResult) => {
        const cls = classifyTrade(item, scoreThreshold, gainThreshold);
        if (cls === "true_positive") return <StatusIndicator type="success">TP ✓</StatusIndicator>;
        if (cls === "true_negative") return <StatusIndicator type="success">TN ✓</StatusIndicator>;
        if (cls === "false_positive") return <StatusIndicator type="error">FP ✗</StatusIndicator>;
        if (cls === "false_negative") return <StatusIndicator type="warning">FN (missed)</StatusIndicator>;
        return "—";
      },
      sortingField: "classification",
      width: 140,
    },
    {
      id: "return_pct",
      header: "Final Return",
      cell: (item: TradeResult) => (
        <Box color={
          (item.return_pct ?? 0) > 0 ? "text-status-success" : "text-status-error"
        }>
          {item.return_pct !== null ? `${item.return_pct.toFixed(1)}%` : "—"}
        </Box>
      ),
      sortingField: "return_pct",
      width: 100,
    },
    {
      id: "max_loss_pct",
      header: "Max Drawdown",
      cell: (item: TradeResult) => (
        <Box color="text-status-error">
          {item.max_loss_pct !== null ? `${item.max_loss_pct.toFixed(1)}%` : "—"}
        </Box>
      ),
      sortingField: "max_loss_pct",
      width: 110,
    },
  ], [scoreThreshold, gainThreshold, result?.horizon_days]);

  return (
    <SpaceBetween size="l">
      {/* Input Form */}
      <Container
        header={
          <Header
            variant="h2"
            description="Test scanner predictions against historical data (no look-ahead bias)"
          >
            Backtest Scanner
          </Header>
        }
      >
        <SpaceBetween size="m">
          <ColumnLayout columns={3}>
            <FormField
              label="As-of Date"
              description="Scanner will only see data up to this date"
            >
              <DatePicker
                value={asOfDate}
                onChange={({ detail }) => setAsOfDate(detail.value)}
                placeholder="YYYY-MM-DD"
                disabled={loading}
              />
            </FormField>
            <FormField
              label="Tickers"
              description="Comma-separated stock symbols"
            >
              <Input
                value={tickers}
                onChange={({ detail }) => setTickers(detail.value)}
                placeholder="AAPL, MSFT, NVDA"
                disabled={loading}
              />
            </FormField>
            <FormField
              label="Horizon (days)"
              description="Forward window to check"
            >
              <Input
                value={horizonDays}
                onChange={({ detail }) => setHorizonDays(detail.value)}
                placeholder="30"
                disabled={loading}
                type="number"
              />
            </FormField>
          </ColumnLayout>
          <Button
            variant="primary"
            onClick={handleBacktest}
            loading={loading}
            iconName="search"
          >
            Run Backtest
          </Button>
        </SpaceBetween>
      </Container>

      {/* Error */}
      {error && (
        <Container>
          <StatusIndicator type="error">{error}</StatusIndicator>
        </Container>
      )}

      {/* Dynamic Threshold Sliders + Confusion Matrix */}
      {trades.length > 0 && (
        <Container
          header={
            <Header
              variant="h2"
              description="Adjust thresholds to see how accuracy changes in real-time"
            >
              Confusion Matrix — {result?.as_of_date} → {result?.horizon_days}d forward
            </Header>
          }
        >
          <SpaceBetween size="l">
            {/* Sliders */}
            <ColumnLayout columns={2}>
              <FormField
                label={`Score Threshold: ${scoreThreshold}`}
                description={`Score ≥ ${scoreThreshold} = "We predict bullish". Lower = more stocks predicted bullish.`}
                constraintText="↑ Higher = stricter (fewer bullish calls) | ↓ Lower = more generous"
              >
                <Slider
                  value={scoreThreshold}
                  onChange={({ detail }) => setScoreThreshold(detail.value)}
                  min={10}
                  max={100}
                  step={5}
                />
              </FormField>
              <FormField
                label={`Gain Threshold: ${gainThreshold}%`}
                description={`Max gain ≥ ${gainThreshold}% = "Stock actually went up". Higher = harder to count as success.`}
                constraintText="↑ Higher = harder bar (more FP, fewer TP) | ↓ Lower = easier bar (more TP)"
              >
                <Slider
                  value={gainThreshold}
                  onChange={({ detail }) => setGainThreshold(detail.value)}
                  min={1}
                  max={25}
                  step={1}
                />
              </FormField>
            </ColumnLayout>

            {/* Plain English Explanation */}
            <Box variant="p" color="text-body-secondary">
              <strong>How to read:</strong> TP = score ≥{scoreThreshold} AND max gain ≥{gainThreshold}% (correctly predicted bullish).
              FP = score ≥{scoreThreshold} BUT gain &lt;{gainThreshold}% (predicted bullish, didn't happen).
              FN = score &lt;{scoreThreshold} BUT gain ≥{gainThreshold}% (missed a bullish stock).
              TN = score &lt;{scoreThreshold} AND gain &lt;{gainThreshold}% (correctly stayed out).
            </Box>

            {/* Confusion Matrix Grid */}
            <ColumnLayout columns={4} variant="text-grid">
              <div>
                <Box variant="awsui-key-label">True Positive</Box>
                <Box variant="h1" color="text-status-success">{cm.tp}</Box>
                <Box variant="small">Score ≥{scoreThreshold} AND gain ≥{gainThreshold}%</Box>
              </div>
              <div>
                <Box variant="awsui-key-label">False Positive</Box>
                <Box variant="h1" color="text-status-error">{cm.fp}</Box>
                <Box variant="small">Score ≥{scoreThreshold} BUT gain &lt;{gainThreshold}%</Box>
              </div>
              <div>
                <Box variant="awsui-key-label">False Negative</Box>
                <Box variant="h1" color="text-status-warning">{cm.fn}</Box>
                <Box variant="small">Score &lt;{scoreThreshold} BUT gain ≥{gainThreshold}%</Box>
              </div>
              <div>
                <Box variant="awsui-key-label">True Negative</Box>
                <Box variant="h1" color="text-status-success">{cm.tn}</Box>
                <Box variant="small">Score &lt;{scoreThreshold} AND gain &lt;{gainThreshold}%</Box>
              </div>
            </ColumnLayout>

            {/* Accuracy Metrics */}
            <ColumnLayout columns={4} variant="text-grid">
              <div>
                <Box variant="awsui-key-label">Accuracy</Box>
                <Box variant="h1" color={cm.accuracy >= 0.6 ? "text-status-success" : "text-status-error"}>
                  {(cm.accuracy * 100).toFixed(0)}%
                </Box>
                <Box variant="small">(TP+TN) / Total</Box>
              </div>
              <div>
                <Box variant="awsui-key-label">Precision</Box>
                <Box variant="h2">{(cm.precision * 100).toFixed(0)}%</Box>
                <Box variant="small">TP / (TP+FP)</Box>
              </div>
              <div>
                <Box variant="awsui-key-label">Recall</Box>
                <Box variant="h2">{(cm.recall * 100).toFixed(0)}%</Box>
                <Box variant="small">TP / (TP+FN)</Box>
              </div>
              <div>
                <Box variant="awsui-key-label">F1 Score</Box>
                <Box variant="h2">{(cm.f1 * 100).toFixed(0)}%</Box>
                <Box variant="small">Balance of precision & recall</Box>
              </div>
            </ColumnLayout>

            {/* Extra Context */}
            <ColumnLayout columns={3} variant="text-grid">
              <div>
                <Box variant="awsui-key-label">Market Regime</Box>
                <Box variant="h3">{result?.market_regime ?? "—"}</Box>
              </div>
              <div>
                <Box variant="awsui-key-label">Trades Analyzed</Box>
                <Box variant="h3">{cm.total}</Box>
              </div>
              <div>
                <Box variant="awsui-key-label">Avg Return</Box>
                <Box variant="h3" color={
                  (result?.metrics?.avg_return ?? 0) >= 0 ? "text-status-success" : "text-status-error"
                }>
                  {(result?.metrics?.avg_return ?? 0).toFixed(1)}%
                </Box>
              </div>
            </ColumnLayout>
          </SpaceBetween>
        </Container>
      )}

      {/* Trade Results Table */}
      {trades.length > 0 && (
        <Table
          key={`${scoreThreshold}-${gainThreshold}`}
          header={
            <Header
              variant="h2"
              description="Each row shows scanner prediction vs actual price movement"
              counter={`(${trades.length})`}
            >
              Trade-by-Trade Results
            </Header>
          }
          columnDefinitions={columnDefinitions}
          items={sortedTrades}
          sortingColumn={sortingColumn}
          sortingDescending={sortingDescending}
          onSortingChange={({ detail }) => {
            setSortingColumn(detail.sortingColumn as { sortingField: string });
            setSortingDescending(detail.isDescending ?? false);
          }}
          variant="container"
          wrapLines
        />
      )}
    </SpaceBetween>
  );
}
