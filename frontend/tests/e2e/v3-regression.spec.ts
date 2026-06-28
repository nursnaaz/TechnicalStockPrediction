import { test, expect } from '@playwright/test';

/**
 * V3 regression: the core scan flow still works AND asserts V3 invariants —
 * the regime badge renders and every shown candidate clears the BUY threshold.
 * Deterministic via route-mock (bullish, all scores >= 65).
 */
const sig = {
  price_above_sma50: true, price_above_ema20: true, macd_above_signal: true,
  macd_histogram_positive: true, volume_above_average: false, relative_strength_positive: true,
};

test('scan flow renders regime badge and only above-threshold candidates', async ({ page }) => {
  await page.route('**/api/v1/scan', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        scan_id: 'reg-1',
        market_regime: 'bullish',
        ranked_tickers: [
          { ticker: 'AAA', bullish_score: 82, signals: sig, current_price: 120, indicators: {} },
          { ticker: 'BBB', bullish_score: 66, signals: sig, current_price: 75, indicators: {} },
        ],
        metadata: { timestamp: new Date().toISOString(), ticker_count: 2, duration_seconds: 0.2 },
      }),
    });
  });

  await page.goto('/');
  await page.locator('input[placeholder*="ticker"]').fill('AAA, BBB');
  await page.locator('button:has-text("Run Scan")').click();

  const badge = page.getByTestId('market-regime-badge');
  await expect(badge).toBeVisible({ timeout: 15000 });
  await expect(badge).toHaveAttribute('data-regime', 'bullish');

  const table = page.locator('table');
  await expect(table).toBeVisible();
  const rows = table.locator('tbody tr');
  await expect(rows).toHaveCount(2);

  // V3 invariant: every score badge shown is >= the bullish threshold (65)
  const scoreCells = await table.locator('tbody tr td:nth-child(3)').allInnerTexts();
  for (const text of scoreCells) {
    const score = parseInt(text.replace(/\D/g, ''), 10);
    expect(score).toBeGreaterThanOrEqual(65);
  }

  await page.screenshot({ path: 'test-results/screenshots/v3-regression.png', fullPage: true });
});
