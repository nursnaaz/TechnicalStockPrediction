// API client for backtesting endpoints

import type { BacktestRequest, BacktestResponse } from '../types/backtest';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Execute a single-date backtest.
 * Runs scanner as of a historical date (no look-ahead) and validates
 * predictions against actual forward price movement.
 */
export async function executeBacktest(request: BacktestRequest): Promise<BacktestResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/backtest/single`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Backtest failed');
  }

  return response.json();
}
