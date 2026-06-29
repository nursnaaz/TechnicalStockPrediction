import { useMemo, useState } from "react";
import Table from "@cloudscape-design/components/table";
import Badge from "@cloudscape-design/components/badge";
import Header from "@cloudscape-design/components/header";
import Box from "@cloudscape-design/components/box";
import Popover from "@cloudscape-design/components/popover";
import type { TickerScore, MarketRegime } from "../types/scan";
import SignalBadges from "./SignalBadges";

interface ResultsTableProps {
  tickers: TickerScore[];
  regime?: MarketRegime;
  scoreThreshold?: number | null;
}

type RankedTicker = TickerScore & { rank: number };

// Human labels + display order for the score-breakdown components.
const BREAKDOWN_ORDER: [string, string][] = [
  ["trend", "Trend"],
  ["momentum", "Momentum"],
  ["strength", "Strength"],
  ["confirmation", "Confirmation"],
  ["stage_pattern", "Stage + Pattern"],
  ["extension_penalty", "Extension penalty"],
  ["climax_penalty", "Climax penalty"],
  ["divergence_penalty", "Divergence penalty"],
];

/**
 * Sortable table of ranked tickers. The score cell is a popover that explains the
 * score by component (when the backend supplies a breakdown).
 */
export default function ResultsTable({ tickers, regime, scoreThreshold }: ResultsTableProps) {
  const getScoreColor = (score: number): "green" | "blue" | "grey" => {
    if (score >= 70) return "green";
    if (score >= 40) return "blue";
    return "grey";
  };

  const showStatus = tickers.some((t) => t.passed_hard_filters != null || t.is_candidate != null);
  const statusBadge = (t: TickerScore) => {
    if (t.is_candidate) return <Badge color="green">Candidate</Badge>;
    if (t.passed_hard_filters) return <Badge color="blue">Below threshold</Badge>;
    return <Badge color="grey">Failed filters</Badge>;
  };

  const scoreBadge = (item: TickerScore) => {
    const badge = <Badge color={getScoreColor(item.bullish_score)}>{item.bullish_score}</Badge>;
    if (!item.score_breakdown) return badge;
    return (
      <Popover
        dismissButton={false}
        position="top"
        size="medium"
        triggerType="custom"
        header={`${item.ticker} — score ${item.bullish_score}`}
        content={
          <Box>
            {BREAKDOWN_ORDER.filter(([k]) => item.score_breakdown![k] !== undefined).map(
              ([k, label]) => {
                const v = item.score_breakdown![k];
                return (
                  <div key={k} style={{ display: "flex", justifyContent: "space-between", gap: 16 }}>
                    <span>{label}</span>
                    <span style={{ color: v < 0 ? "#a50e0e" : "#137333", fontWeight: 600 }}>
                      {v > 0 ? `+${v}` : v}
                    </span>
                  </div>
                );
              }
            )}
          </Box>
        }
      >
        <span style={{ cursor: "pointer" }} data-testid="score-popover-trigger">
          {badge}
        </span>
      </Popover>
    );
  };

  const ranked: RankedTicker[] = tickers.map((ticker, index) => ({ ...ticker, rank: index + 1 }));

  const columnDefinitions = [
    {
      id: "rank",
      header: "Rank",
      cell: (item: RankedTicker) => <Box textAlign="center">{item.rank}</Box>,
      width: 80,
    },
    {
      id: "ticker",
      header: "Ticker",
      cell: (item: RankedTicker) => <strong>{item.ticker}</strong>,
      sortingComparator: (a: RankedTicker, b: RankedTicker) => a.ticker.localeCompare(b.ticker),
      width: 100,
    },
    {
      id: "score",
      header: "Bullish Score",
      cell: (item: RankedTicker) => scoreBadge(item),
      sortingComparator: (a: RankedTicker, b: RankedTicker) => a.bullish_score - b.bullish_score,
      width: 130,
    },
    ...(showStatus
      ? [
          {
            id: "status",
            header: "Status",
            cell: (item: RankedTicker) => statusBadge(item),
            width: 150,
          },
        ]
      : []),
    {
      id: "price",
      header: "Price",
      cell: (item: RankedTicker) => `$${item.current_price.toFixed(2)}`,
      sortingComparator: (a: RankedTicker, b: RankedTicker) => a.current_price - b.current_price,
      width: 100,
    },
    {
      id: "signals",
      header: "Active Signals",
      cell: (item: RankedTicker) => <SignalBadges signals={item.signals} />,
    },
  ];

  // Cloudscape doesn't sort for us — keep sort state and apply the column's comparator.
  const [sortingColumn, setSortingColumn] = useState<(typeof columnDefinitions)[number] | undefined>();
  const [sortingDescending, setSortingDescending] = useState(false);

  const sortedItems = useMemo(() => {
    const cmp = sortingColumn?.sortingComparator;
    if (!cmp) return ranked;
    const out = [...ranked].sort(cmp);
    return sortingDescending ? out.reverse() : out;
  }, [ranked, sortingColumn, sortingDescending]);

  return (
    <Table
      header={
        <Header
          counter={`(${tickers.length})`}
          description={
            showStatus
              ? `All scanned stocks — Candidate = passed hard filters AND score ≥ ${scoreThreshold ?? 65}. Click a score to see its breakdown.`
              : "Ranked by bullish score · click a score to see its breakdown · click a column to sort"
          }
        >
          {showStatus ? "All Scanned Stocks" : "Ranked Results"}
        </Header>
      }
      columnDefinitions={columnDefinitions}
      items={sortedItems}
      variant="container"
      sortingColumn={sortingColumn}
      sortingDescending={sortingDescending}
      onSortingChange={({ detail }) => {
        setSortingColumn(detail.sortingColumn);
        setSortingDescending(detail.isDescending);
      }}
      empty={
        <Box textAlign="center" color="inherit" data-testid="results-empty">
          {regime === "bearish" ? (
            <>
              <b>No signals in a bearish market</b>
              <Box variant="p" color="inherit">
                The market is below its 200-day trend, so V3 emits zero buy candidates. Wait for the
                market to recover.
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
