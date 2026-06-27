// Type definitions for backtesting

export interface BacktestRequest {
  as_of_date: string;
  tickers: string[];
  horizon_days: number;
}

export interface TradeResult {
  ticker: string;
  entry_price: number;
  final_price: number | null;
  score: number;
  signals: Record<string, boolean> | null;
  days_tracked: number | null;
  return_pct: number | null;
  max_gain_pct: number | null;
  max_loss_pct: number | null;
  max_price: number | null;
  is_winner: boolean | null;
  predicted_bullish: boolean | null;
  actually_went_up: boolean | null;
  classification: string | null;
  hit_target_1: boolean | null;
  hit_target_2: boolean | null;
  hit_stop: boolean | null;
  status: string;
}

export interface ScoreBucketMetrics {
  count: number;
  win_rate: number;
  avg_return: number;
}

export interface BacktestMetrics {
  total_trades: number;
  win_count: number | null;
  loss_count: number | null;
  win_rate: number | null;
  avg_return: number | null;
  avg_winner: number | null;
  avg_loser: number | null;
  reward_risk_ratio: number | null;
  expectancy: number | null;
  best_trade: number | null;
  worst_trade: number | null;
  target_1_hit_count: number | null;
  target_1_hit_rate: number | null;
  target_2_hit_count: number | null;
  target_2_hit_rate: number | null;
  stop_hit_count: number | null;
  stop_hit_rate: number | null;
  confusion_matrix: {
    true_positive: number;
    false_positive: number;
    false_negative: number;
    true_negative: number;
  } | null;
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
  by_score_bucket: Record<string, ScoreBucketMetrics> | null;
  error: string | null;
}

export interface BacktestResponse {
  backtest_id: string;
  status: string;
  as_of_date: string;
  horizon_days: number | null;
  scan_id: string | null;
  market_regime: string | null;
  total_candidates: number | null;
  trades_analyzed: number | null;
  metrics: BacktestMetrics | null;
  trades: TradeResult[] | null;
  error: string | null;
}
