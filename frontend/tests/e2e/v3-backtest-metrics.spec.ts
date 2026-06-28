import { test, expect } from '@playwright/test';

/**
 * V3: the Backtest tab renders the confusion matrix + precision/recall and the
 * threshold slider re-buckets the metrics live. Deterministic via route-mock.
 */
function trade(ticker: string, score: number, gain: number) {
  return {
    ticker, entry_price: 100, score, signals: {}, days_tracked: 30,
    return_pct: gain, max_gain_pct: gain, max_loss_pct: -2, max_price: 100 + gain,
    is_winner: gain > 0, predicted_bullish: score >= 65, actually_went_up: gain >= 5,
    classification: 'x', hit_target_1: false, hit_target_2: false, hit_stop: false,
    status: 'analyzed',
  };
}

test('backtest tab shows confusion matrix + precision and slider re-buckets', async ({ page }) => {
  await page.route('**/api/v1/backtest/single', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        backtest_id: 'bt-1', status: 'completed', as_of_date: '2025-02-01',
        horizon_days: 30, scan_id: 's1', market_regime: 'bullish',
        total_candidates: 4, trades_analyzed: 4,
        trades: [trade('A', 80, 12), trade('B', 75, 1), trade('C', 40, 9), trade('D', 30, 1)],
        metrics: {},
      }),
    });
  });

  await page.goto('/');
  await page.getByRole('tab', { name: 'Backtest' }).click();

  const dateInput = page.locator('input[placeholder="YYYY-MM-DD"]');
  await dateInput.click();
  await dateInput.pressSequentially('2025/02/01', { delay: 20 });
  await page.keyboard.press('Escape');
  await page.locator('input[placeholder*="AAPL"]').fill('A, B, C, D');
  await page.getByRole('button', { name: 'Run', exact: true }).click();

  // Metrics + confusion matrix render
  await expect(page.getByTestId('metric-precision')).toBeVisible({ timeout: 15000 });
  for (const cell of ['cm-tp', 'cm-fp', 'cm-fn', 'cm-tn']) {
    await expect(page.getByTestId(cell)).toBeVisible();
  }

  // Slider re-buckets: bump score threshold via keyboard, label updates 50 -> 55
  const slider = page.locator('[data-testid="score-threshold-slider"] input[type="range"]');
  await slider.focus();
  await slider.press('ArrowRight');
  await expect(page.getByText(/Score Threshold:\s*55/)).toBeVisible();

  await page.screenshot({ path: 'test-results/screenshots/v3-backtest-metrics.png', fullPage: true });
});
