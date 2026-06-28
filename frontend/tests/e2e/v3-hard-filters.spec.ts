import { test, expect } from '@playwright/test';

/**
 * V3: only hard-filter-passing leaders that clear the threshold are surfaced.
 * Route-mock returns a response where a weak ticker has already been excluded by
 * the backend; we assert the leader is shown, the weak name is absent, and rows
 * are ranked descending by score.
 */
const sig = {
  price_above_sma50: true, price_above_ema20: true, macd_above_signal: true,
  macd_histogram_positive: true, volume_above_average: true, relative_strength_positive: true,
};

test('hard-filter survivors shown, weak names absent, ranked by score', async ({ page }) => {
  await page.route('**/api/v1/scan', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        scan_id: 'test-hf',
        market_regime: 'bullish',
        ranked_tickers: [
          { ticker: 'LEADER', bullish_score: 88, signals: sig, current_price: 150.0, indicators: {} },
          { ticker: 'SECOND', bullish_score: 70, signals: sig, current_price: 90.0, indicators: {} },
        ],
        metadata: { timestamp: new Date().toISOString(), ticker_count: 2, duration_seconds: 0.2 },
      }),
    });
  });

  await page.goto('/');
  await page.locator('input[placeholder*="ticker"]').fill('LEADER, SECOND, WEAK');
  await page.locator('button:has-text("Run Scan")').click();

  const table = page.locator('table');
  await expect(table).toBeVisible({ timeout: 15000 });

  await expect(table).toContainText('LEADER');
  await expect(table).toContainText('SECOND');
  await expect(table).not.toContainText('WEAK');  // excluded by hard filters

  // Ranked descending: first data row is the highest score
  const firstRow = table.locator('tbody tr').first();
  await expect(firstRow).toContainText('LEADER');
  await expect(firstRow).toContainText('88');

  await page.screenshot({ path: 'test-results/screenshots/v3-hard-filters.png', fullPage: true });
});
