import Table from "@cloudscape-design/components/table";
import Badge from "@cloudscape-design/components/badge";
import Header from "@cloudscape-design/components/header";
import Box from "@cloudscape-design/components/box";
import type { TickerScore, MarketRegime } from "../types/scan";
import SignalBadges from "./SignalBadges";

interface ResultsTableProps {
  tickers: TickerScore[];
  regime?: MarketRegime;
  scoreThreshold?: number | null;
}

/**
 * Table component displaying ranked tickers with scores and signals
 */
export default function ResultsTable({ tickers, regime, scoreThreshold }: ResultsTableProps) {
  const getScoreColor = (score: number): "green" | "blue" | "grey" => {
    if (score >= 70) return "green";
    if (score >= 40) return "blue";
    return "grey";
  };

  // "Show all scanned" mode populates these diagnostic flags; show a Status column then.
  const showStatus = tickers.some((t) => t.passed_hard_filters != null || t.is_candidate != null);
  const statusBadge = (t: TickerScore) => {
    if (t.is_candidate) return <Badge color="green">Candidate</Badge>;
    if (t.passed_hard_filters) return <Badge color="blue">Below threshold</Badge>;
    return <Badge color="grey">Failed filters</Badge>;
  };

  // Add rank to items for display
  const rankedItems = tickers.map((ticker, index) => ({
    ...ticker,
    rank: index + 1,
  }));

  return (
    <Table
      header={
        <Header
          counter={`(${tickers.length})`}
          description={
            showStatus
              ? `All scanned stocks — Candidate = passed hard filters AND score ≥ ${scoreThreshold ?? 65}`
              : "Stocks ranked by bullish score"
          }
        >
          {showStatus ? "All Scanned Stocks" : "Ranked Results"}
        </Header>
      }
      columnDefinitions={[
        {
          id: "rank",
          header: "Rank",
          cell: (item) => <Box textAlign="center">{item.rank}</Box>,
          width: 80,
        },
        {
          id: "ticker",
          header: "Ticker",
          cell: (item) => <strong>{item.ticker}</strong>,
          width: 100,
        },
        {
          id: "score",
          header: "Bullish Score",
          cell: (item) => (
            <Badge color={getScoreColor(item.bullish_score)}>
              {item.bullish_score}
            </Badge>
          ),
          width: 120,
        },
        ...(showStatus
          ? [{
              id: "status",
              header: "Status",
              cell: (item: TickerScore) => statusBadge(item),
              width: 150,
            }]
          : []),
        {
          id: "price",
          header: "Price",
          cell: (item) => `$${item.current_price.toFixed(2)}`,
          width: 100,
        },
        {
          id: "signals",
          header: "Active Signals",
          cell: (item) => <SignalBadges signals={item.signals} />,
        },
      ]}
      items={rankedItems}
      variant="container"
      empty={
        <Box textAlign="center" color="inherit" data-testid="results-empty">
          {regime === "bearish" ? (
            <>
              <b>No signals in a bearish market</b>
              <Box variant="p" color="inherit">
                The market is below its 200-day trend, so V3 emits zero buy
                candidates. Wait for the market to recover.
              </Box>
            </>
          ) : (
            <>
              <b>No qualifying candidates</b>
              <Box variant="p" color="inherit">
                No tickers passed the V3 filters and score threshold for this scan.
              </Box>
            </>
          )}
        </Box>
      }
    />
  );
}
