import Table from "@cloudscape-design/components/table";
import Badge from "@cloudscape-design/components/badge";
import Header from "@cloudscape-design/components/header";
import Box from "@cloudscape-design/components/box";
import type { TickerScore } from "../types/scan";
import SignalBadges from "./SignalBadges";

interface ResultsTableProps {
  tickers: TickerScore[];
}

/**
 * Table component displaying ranked tickers with scores and signals
 */
export default function ResultsTable({ tickers }: ResultsTableProps) {
  const getScoreColor = (score: number): "green" | "blue" | "grey" => {
    if (score >= 70) return "green";
    if (score >= 40) return "blue";
    return "grey";
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
          description="Stocks ranked by bullish score"
        >
          Ranked Results
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
        <Box textAlign="center" color="inherit">
          <b>No results</b>
          <Box variant="p" color="inherit">
            No tickers were successfully analyzed.
          </Box>
        </Box>
      }
    />
  );
}
