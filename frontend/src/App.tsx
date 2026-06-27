import { useState } from "react";
import AppLayout from "@cloudscape-design/components/app-layout";
import ContentLayout from "@cloudscape-design/components/content-layout";
import Header from "@cloudscape-design/components/header";
import Container from "@cloudscape-design/components/container";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Input from "@cloudscape-design/components/input";
import Tabs from "@cloudscape-design/components/tabs";
import "@cloudscape-design/global-styles/index.css";

import ScanButton from "./components/ScanButton";
import LoadingIndicator from "./components/LoadingIndicator";
import MarketRegimeBadge from "./components/MarketRegimeBadge";
import ResultsTable from "./components/ResultsTable";
import ErrorMessage from "./components/ErrorMessage";
import BacktestPanel from "./components/BacktestPanel";
import { executeScan } from "./services/scanApi";
import type { ScanResponse } from "./types/scan";

function App() {
  const [tickers, setTickers] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<ScanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleScan = async () => {
    // Validate input
    if (!tickers.trim()) {
      setError("Please enter at least one ticker symbol");
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      // Parse tickers from input (comma or space separated)
      const tickerList = tickers
        .split(/[,\s]+/)
        .map((t) => t.trim().toUpperCase())
        .filter((t) => t.length > 0);

      if (tickerList.length === 0) {
        setError("Please enter at least one valid ticker symbol");
        return;
      }

      // Execute scan
      const data = await executeScan(tickerList);
      setResults(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Scan failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (event: CustomEvent<{ key: string }>) => {
    if (event.detail.key === "Enter" && !loading) {
      handleScan();
    }
  };

  return (
    <AppLayout
      content={
        <ContentLayout
          header={
            <Header
              variant="h1"
              description="Analyze technical indicators to identify potentially bullish stocks"
            >
              Bullish Stock Scanner
            </Header>
          }
        >
          <Tabs
            tabs={[
              {
                label: "Live Scanner",
                id: "scanner",
                content: (
                  <SpaceBetween size="l">
                    <Container>
                      <SpaceBetween size="m">
                        <Input
                          value={tickers}
                          onChange={({ detail }) => setTickers(detail.value)}
                          placeholder="Enter ticker symbols (e.g., AAPL, MSFT, GOOGL)"
                          disabled={loading}
                          onKeyDown={handleKeyPress}
                        />
                        <ScanButton onClick={handleScan} loading={loading} />
                      </SpaceBetween>
                    </Container>

                    {error && <ErrorMessage message={error} onDismiss={() => setError(null)} />}

                    {loading && <LoadingIndicator message="Analyzing stocks..." />}

                    {results && (
                      <SpaceBetween size="m">
                        <MarketRegimeBadge regime={results.market_regime} />
                        <ResultsTable tickers={results.ranked_tickers} />
                      </SpaceBetween>
                    )}
                  </SpaceBetween>
                ),
              },
              {
                label: "Backtest",
                id: "backtest",
                content: <BacktestPanel />,
              },
            ]}
          />
        </ContentLayout>
      }
      navigationHide
      toolsHide
    />
  );
}

export default App;
