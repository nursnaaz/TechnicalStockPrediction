// Type definitions for the Bullish Stock Scanner

export type MarketRegime = "bullish" | "bearish" | "neutral";

export interface IndicatorSignals {
  price_above_sma50: boolean;
  price_above_ema20: boolean;
  macd_above_signal: boolean;
  macd_histogram_positive: boolean;
  volume_above_average: boolean;
  relative_strength_positive: boolean;
}

export interface TickerScore {
  ticker: string;
  bullish_score: number;
  signals: IndicatorSignals;
  current_price: number;
  indicators: {
    sma_50?: number | null;
    ema_20?: number | null;
    macd_line?: number | null;
    macd_signal?: number | null;
    macd_histogram?: number | null;
    avg_volume_20?: number | null;
    relative_strength?: number | null;
  };
  // V3 diagnostic fields (present when include_all is requested)
  passed_hard_filters?: boolean | null;
  is_candidate?: boolean | null;
  // Per-component point contributions (trend/momentum/strength/confirmation/stage_pattern/penalties).
  score_breakdown?: Record<string, number> | null;
}

export interface ScanMetadata {
  timestamp: string;
  ticker_count: number;
  duration_seconds: number;
}

export interface ScanResponse {
  scan_id: string;
  market_regime: MarketRegime;
  ranked_tickers: TickerScore[];
  metadata: ScanMetadata;
  score_threshold?: number | null;
}

export interface ScanRequest {
  tickers: string[];
  include_all?: boolean;
}
